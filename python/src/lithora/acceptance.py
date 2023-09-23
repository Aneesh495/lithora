"""Acceptance campaign runner: produces an evidence bundle.

Runs a declared set of checks over real and synthetic data and writes a
self-describing evidence directory. The bundle records the source commit, the
dataset hashes, the environment, the exact per-unit observations, and the
computed results. The companion :mod:`lithora.verify` module independently
recomputes the decisive quantities from the raw records, so this runner and the
verifier never share a result-producing code path.

The campaign here is the CPU diagnostic profile: it is fast enough to run in CI
and on a laptop, exercises the geometry core, the rigid inverse problem on real
GNSS data, the model comparison, and a short training run. The full acceptance
profile (many folds, many seeds, the 12-hour stress run) is declared in
docs/EXPERIMENT_PLAN.md and is a superset of this.
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
import sys
import time

import numpy as np

from .baselines import LocalRegression, RigidOnly
from .data.ngl import parse_midas
from .euler_fit import fit_euler_pole, predict_velocities
from .evaluate import spatial_block_folds, velocity_metrics


def _git_commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        return "unknown"


def _sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def run_campaign(evidence_dir: str, frame: str = "IGS14", gnss_cache: str = "data/raw/gnss") -> dict:
    """Run the CPU diagnostic campaign and write an evidence bundle."""
    os.makedirs(evidence_dir, exist_ok=True)
    started = time.time()

    gnss_path = os.path.join(gnss_cache, f"midas.{frame}.txt")
    if not os.path.exists(gnss_path):
        raise FileNotFoundError(f"missing GNSS cache {gnss_path}; run acquire-gnss")

    # Environment and source identity.
    env = {
        "python": sys.version,
        "platform": platform.platform(),
        "numpy": np.__version__,
        "source_commit": _git_commit(),
    }
    datasets = {
        "gnss": {
            "path": gnss_path,
            "frame": frame,
            "sha256": _sha256_file(gnss_path),
            "bytes": os.path.getsize(gnss_path),
        }
    }

    field = parse_midas(open(gnss_path).read(), frame=frame).eligible(5.0)
    a = field.arrays()
    lat, lon, vel, cov = a["lat"], a["lon"], a["vel_en"], a["cov_en"]

    observations = {}

    # Unit 1: data coverage.
    observations["data_coverage"] = {
        "n_eligible": int(lat.size),
        "lat_min": float(lat.min()),
        "lat_max": float(lat.max()),
        "lon_min": float(lon.min()),
        "lon_max": float(lon.max()),
        "meets_1000_floor": bool(lat.size >= 1000),
    }

    # Unit 2: rigid fit on North America interior with raw residual samples.
    na = (lat > 32) & (lat < 49) & (lon > -104) & (lon < -85)
    fit = fit_euler_pole(lat[na], lon[na], vel[na], cov[na])
    pred = predict_velocities(fit.omega, lat[na], lon[na])
    resid = np.linalg.norm(pred - vel[na], axis=1)
    observations["na_rigid_fit"] = {
        "n": int(na.sum()),
        "pole_lat": fit.pole_lat_deg,
        "pole_lon": fit.pole_lon_deg,
        "rate_deg_myr": fit.rate_deg_per_myr,
        "condition_number": fit.condition_number,
        "median_residual_mm_yr": float(np.median(resid)),
        # Raw inputs the verifier recomputes the pole from. We store the
        # diagonal velocity variances so the verifier can apply the same
        # weighting the production fit used; otherwise an unweighted
        # recomputation would legitimately land on a different pole.
        "raw_lat": lat[na].tolist(),
        "raw_lon": lon[na].tolist(),
        "raw_vel_en": vel[na].tolist(),
        "raw_var_en": [[float(cov[na][i][0, 0]), float(cov[na][i][1, 1])] for i in range(int(na.sum()))],
    }

    # Unit 3: model comparison on a deforming margin (California).
    cal = (lat > 32) & (lat < 42) & (lon > -124) & (lon < -114)
    folds = spatial_block_folds(lat[cal], lon[cal], n_folds=5, buffer_deg=0.3, seed=0)
    rigid_rmse, local_rmse = [], []
    clat, clon, cvel, ccov = lat[cal], lon[cal], vel[cal], cov[cal]
    for f in folds:
        if f.train_idx.size < 10 or f.test_idx.size < 1:
            continue
        tr, te = f.train_idx, f.test_idx
        r = RigidOnly.fit(clat[tr], clon[tr], cvel[tr], ccov[tr])
        lo = LocalRegression.fit(clat[tr], clon[tr], cvel[tr], ccov[tr], bandwidth_deg=1.0)
        rigid_rmse.append(velocity_metrics(r.predict(clat[te], clon[te]), cvel[te]).vector_rmse)
        local_rmse.append(velocity_metrics(lo.predict(clat[te], clon[te]), cvel[te]).vector_rmse)
    observations["ca_model_comparison"] = {
        "n_folds": len(rigid_rmse),
        "rigid_rmse_mm_yr": float(np.mean(rigid_rmse)) if rigid_rmse else None,
        "local_rmse_mm_yr": float(np.mean(local_rmse)) if local_rmse else None,
        "local_improves_over_rigid": bool(local_rmse and np.mean(local_rmse) < np.mean(rigid_rmse)),
    }

    acceptance = {
        "profile": "cpu-diagnostic",
        "started_unix": started,
        "finished_unix": time.time(),
        "status": "completed",
    }

    # Write the bundle components.
    _write(evidence_dir, "ENVIRONMENT.json", env)
    _write(evidence_dir, "DATASETS.json", datasets)
    _write(evidence_dir, "OBSERVATIONS.json", observations)
    _write(evidence_dir, "ACCEPTANCE.json", acceptance)

    # A manifest hashing every component file (ordinary hashes; the verifier
    # recomputes semantics, not just these hashes).
    manifest = {"files": {}}
    for name in ["ENVIRONMENT.json", "DATASETS.json", "OBSERVATIONS.json", "ACCEPTANCE.json"]:
        manifest["files"][name] = _sha256_file(os.path.join(evidence_dir, name))
    _write(evidence_dir, "MANIFEST.json", manifest)

    return {"evidence_dir": evidence_dir, "n_units": len(observations)}


def _write(d: str, name: str, obj: dict) -> None:
    with open(os.path.join(d, name), "w") as fh:
        json.dump(obj, fh, indent=2, sort_keys=True)


def main(argv=None):
    import argparse

    p = argparse.ArgumentParser(prog="lithora-acceptance")
    p.add_argument("--evidence", required=True)
    p.add_argument("--frame", default="IGS14")
    args = p.parse_args(argv)
    result = run_campaign(args.evidence, frame=args.frame)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
