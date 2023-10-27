"""Command-line entry point for the Lithora Python inference layer.

Wires acquisition, rigid-plate fitting, spatial evaluation, and training into
a single tool so the Makefile targets and a fresh reader drive the same code
paths the tests exercise. Each subcommand prints a compact JSON summary and
writes any artifacts under ``runs/`` (gitignored).

Usage:
    python -m lithora.cli acquire-gnss --frame IGS14
    python -m lithora.cli fit-plates --frame IGS14
    python -m lithora.cli spatial-evaluate --frame IGS14 --region na
    python -m lithora.cli train --frame IGS14 --region na
"""

from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np

from .baselines import LocalRegression, NearestNeighbor, RigidOnly
from .data.ngl import parse_midas
from .euler_fit import fit_euler_pole, predict_velocities
from .evaluate import distance_to_training, spatial_block_folds, velocity_metrics
from .gp import GPResidual

# Regional boxes selected by data coverage, not desired conclusions.
REGIONS = {
    "na": (32.0, 49.0, -104.0, -85.0, "North America interior"),
    "cal": (32.0, 42.0, -124.0, -114.0, "California transform margin"),
    "jpn": (30.0, 46.0, 128.0, 146.0, "Japan convergent margin"),
    "eu": (40.0, 60.0, 0.0, 30.0, "Central Europe"),
    "au": (-40.0, -15.0, 113.0, 153.0, "Australia interior"),
}


def _load_field(frame: str, cache_dir: str = "data/raw/gnss"):
    path = os.path.join(cache_dir, f"midas.{frame}.txt")
    if not os.path.exists(path):
        print(
            f"error: no cached GNSS file at {path}. Run acquire-gnss first.",
            file=sys.stderr,
        )
        sys.exit(2)
    return parse_midas(open(path).read(), frame=frame)


def _region_mask(lat, lon, region: str):
    if region == "all":
        return np.ones(lat.size, dtype=bool), "global"
    if region not in REGIONS:
        print(f"error: unknown region '{region}'; known: {sorted(REGIONS)}", file=sys.stderr)
        sys.exit(2)
    lo_lat, hi_lat, lo_lon, hi_lon, label = REGIONS[region]
    mask = (lat > lo_lat) & (lat < hi_lat) & (lon > lo_lon) & (lon < hi_lon)
    return mask, label


def cmd_acquire_gnss(args):
    from .data.acquire import acquire_gnss

    field = acquire_gnss(frame=args.frame)
    elig = field.eligible(min_years=args.min_years)
    print(json.dumps({
        "frame": field.frame,
        "n_stations": len(field),
        "n_eligible": len(elig),
        "min_years": args.min_years,
    }, indent=2))


def cmd_fit_plates(args):
    field = _load_field(args.frame).eligible(args.min_years)
    a = field.arrays()
    mask, label = _region_mask(a["lat"], a["lon"], args.region)
    n = int(mask.sum())
    if n < 5:
        print(json.dumps({"region": label, "n_stations": n, "error": "too few stations"}))
        return
    fit = fit_euler_pole(a["lat"][mask], a["lon"][mask], a["vel_en"][mask], a["cov_en"][mask])
    pred = predict_velocities(fit.omega, a["lat"][mask], a["lon"][mask])
    resid = np.linalg.norm(pred - a["vel_en"][mask], axis=1)
    print(json.dumps({
        "region": label,
        "frame": args.frame,
        "n_stations": n,
        "pole_lat_deg": round(fit.pole_lat_deg, 3),
        "pole_lon_deg": round(fit.pole_lon_deg, 3),
        "rate_deg_per_myr": round(fit.rate_deg_per_myr, 5),
        "condition_number": float(f"{fit.condition_number:.3e}"),
        "rank_deficient": fit.rank_deficient,
        "median_residual_mm_yr": round(float(np.median(resid)), 3),
        "median_observed_mm_yr": round(float(np.median(np.linalg.norm(a["vel_en"][mask], axis=1))), 3),
    }, indent=2))


def cmd_spatial_evaluate(args):
    field = _load_field(args.frame).eligible(args.min_years)
    a = field.arrays()
    mask, label = _region_mask(a["lat"], a["lon"], args.region)
    lat, lon, vel, cov = a["lat"][mask], a["lon"][mask], a["vel_en"][mask], a["cov_en"][mask]
    if lat.size < 40:
        print(json.dumps({"region": label, "n": int(lat.size), "error": "too few stations"}))
        return

    folds = spatial_block_folds(lat, lon, n_folds=args.folds, buffer_deg=args.buffer, seed=0)
    results = {name: [] for name in ["rigid", "nn", "local", "gp"]}
    coverage = []
    for f in folds:
        if f.train_idx.size < 10 or f.test_idx.size < 1:
            continue
        tr, te = f.train_idx, f.test_idx
        models = {
            "rigid": RigidOnly.fit(lat[tr], lon[tr], vel[tr], cov[tr]),
            "nn": NearestNeighbor.fit(lat[tr], lon[tr], vel[tr], cov[tr]),
            "local": LocalRegression.fit(lat[tr], lon[tr], vel[tr], cov[tr], bandwidth_deg=args.bandwidth),
            "gp": GPResidual.fit(lat[tr], lon[tr], vel[tr], cov[tr]),
        }
        d2t = distance_to_training(lat[te], lon[te], lat[tr], lon[tr])
        for name, model in models.items():
            if name == "gp":
                pred, std = model.predict(lat[te], lon[te], return_std=True)
                m = velocity_metrics(pred, vel[te], std_en=std, dist_to_train_rad=d2t)
                coverage.append(m.coverage_1sigma)
            else:
                pred = model.predict(lat[te], lon[te])
                m = velocity_metrics(pred, vel[te], dist_to_train_rad=d2t)
            results[name].append(m.vector_rmse)

    summary = {
        "region": label,
        "frame": args.frame,
        "n_stations": int(lat.size),
        "n_folds_used": len(results["rigid"]),
        "buffer_deg": args.buffer,
        "vector_rmse_mm_yr": {k: round(float(np.mean(v)), 3) for k, v in results.items() if v},
        "gp_mean_1sigma_coverage": round(float(np.mean([c for c in coverage if c is not None])), 3) if coverage else None,
    }
    print(json.dumps(summary, indent=2))


def cmd_leave_region_out(args):
    """Train on one region and test on another, measuring transfer.

    This is the leave-region-out experiment: it quantifies how well a model
    fit on one tectonic setting predicts another, which is the hardest and
    most honest generalisation test. A rigid pole fit on a quiet interior
    should transfer poorly to a deforming margin, and the numbers show it.
    """
    field = _load_field(args.frame).eligible(args.min_years)
    a = field.arrays()
    train_mask, train_label = _region_mask(a["lat"], a["lon"], args.train_region)
    test_mask, test_label = _region_mask(a["lat"], a["lon"], args.test_region)

    tr = np.where(train_mask)[0]
    te = np.where(test_mask)[0]
    if tr.size < 10 or te.size < 10:
        print(json.dumps({"error": "too few stations", "n_train": int(tr.size), "n_test": int(te.size)}))
        return

    lat, lon, vel, cov = a["lat"], a["lon"], a["vel_en"], a["cov_en"]
    rigid = RigidOnly.fit(lat[tr], lon[tr], vel[tr], cov[tr])
    local = LocalRegression.fit(lat[tr], lon[tr], vel[tr], cov[tr], bandwidth_deg=args.bandwidth)

    from .evaluate import distance_to_training, velocity_metrics

    d2t = distance_to_training(lat[te], lon[te], lat[tr], lon[tr])
    rigid_m = velocity_metrics(rigid.predict(lat[te], lon[te]), vel[te], dist_to_train_rad=d2t)
    local_m = velocity_metrics(local.predict(lat[te], lon[te]), vel[te], dist_to_train_rad=d2t)

    print(json.dumps({
        "train_region": train_label,
        "test_region": test_label,
        "n_train": int(tr.size),
        "n_test": int(te.size),
        "median_test_distance_to_train_deg": round(float(np.degrees(np.median(d2t))), 2),
        "rigid_test_rmse_mm_yr": round(rigid_m.vector_rmse, 3),
        "local_test_rmse_mm_yr": round(local_m.vector_rmse, 3),
        "note": "cross-region transfer; large distance to training network is expected",
    }, indent=2))


def cmd_train(args):
    from .graph_model import torch_available

    if not torch_available():
        print(json.dumps({"error": "PyTorch not installed; install python/.[learn]"}))
        sys.exit(2)
    from .train import predict_training_nodes, train_graph_model

    field = _load_field(args.frame).eligible(args.min_years)
    a = field.arrays()
    mask, label = _region_mask(a["lat"], a["lon"], args.region)
    lat, lon, vel, cov = a["lat"][mask], a["lon"][mask], a["vel_en"][mask], a["cov_en"][mask]
    if lat.size < 40:
        print(json.dumps({"region": label, "n": int(lat.size), "error": "too few stations"}))
        return

    rng = np.random.default_rng(args.seed)
    tr_mask = rng.random(lat.size) < 0.8
    model, ctx, res = train_graph_model(
        lat, lon, vel, cov, train_mask=tr_mask, epochs=args.epochs, seed=args.seed
    )
    pred = predict_training_nodes(model, ctx)
    held = ~tr_mask
    err = np.linalg.norm(pred[held] - vel[held], axis=1)
    rigid = predict_velocities(res_omega(ctx), lat[held], lon[held])
    rigid_err = np.linalg.norm(rigid - vel[held], axis=1)
    print(json.dumps({
        "region": label,
        "n_stations": int(lat.size),
        "n_params": res.n_params,
        "initial_loss": round(res.initial_loss, 4),
        "final_loss": round(res.final_loss, 4),
        "param_delta_l2": round(res.param_delta_l2, 4),
        "held_out_graph_rmse_mm_yr": round(float(np.sqrt(np.mean(err**2))), 3),
        "held_out_rigid_rmse_mm_yr": round(float(np.sqrt(np.mean(rigid_err**2))), 3),
    }, indent=2))


def res_omega(ctx):
    return ctx["omega"]


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="lithora", description="Lithora inference CLI")
    sub = p.add_subparsers(dest="command", required=True)

    a = sub.add_parser("acquire-gnss", help="download NGL MIDAS velocities")
    a.add_argument("--frame", default="IGS14")
    a.add_argument("--min-years", type=float, default=5.0)
    a.set_defaults(func=cmd_acquire_gnss)

    f = sub.add_parser("fit-plates", help="rigid Euler-pole fit for a region")
    f.add_argument("--frame", default="IGS14")
    f.add_argument("--region", default="na")
    f.add_argument("--min-years", type=float, default=5.0)
    f.set_defaults(func=cmd_fit_plates)

    e = sub.add_parser("spatial-evaluate", help="buffered spatial CV of baselines")
    e.add_argument("--frame", default="IGS14")
    e.add_argument("--region", default="na")
    e.add_argument("--min-years", type=float, default=5.0)
    e.add_argument("--folds", type=int, default=5)
    e.add_argument("--buffer", type=float, default=0.5)
    e.add_argument("--bandwidth", type=float, default=2.0)
    e.set_defaults(func=cmd_spatial_evaluate)

    lro = sub.add_parser("leave-region-out", help="train on one region, test on another")
    lro.add_argument("--frame", default="IGS14")
    lro.add_argument("--train-region", default="na")
    lro.add_argument("--test-region", default="cal")
    lro.add_argument("--min-years", type=float, default=5.0)
    lro.add_argument("--bandwidth", type=float, default=1.5)
    lro.set_defaults(func=cmd_leave_region_out)

    t = sub.add_parser("train", help="train the spherical graph residual model")
    t.add_argument("--frame", default="IGS14")
    t.add_argument("--region", default="na")
    t.add_argument("--min-years", type=float, default=5.0)
    t.add_argument("--epochs", type=int, default=300)
    t.add_argument("--seed", type=int, default=0)
    t.set_defaults(func=cmd_train)

    return p


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
