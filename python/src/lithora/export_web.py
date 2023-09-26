"""Export real inference outputs to static assets the web globe consumes.

The globe must show real data, not a hardcoded array. This module writes a
compact JSON of station positions, observed velocities, the rigid-model
prediction, the residual, and the fold/holdout membership for a chosen region,
plus an earthquake context layer. Each file carries the provenance and the
reference frame so the globe can label its layers honestly.

Output goes to web/public/data (committed as a small sample so the globe runs
from a fresh checkout) or a larger generated set under runs/ (gitignored).
"""

from __future__ import annotations

import json
import os

import numpy as np

from .baselines import LocalRegression, RigidOnly
from .data.ngl import parse_midas
from .euler_fit import fit_euler_pole, predict_velocities
from .evaluate import spatial_block_folds

REGION_BOXES = {
    "cal": (32.0, 42.0, -124.0, -114.0, "California transform margin"),
    "na": (32.0, 49.0, -104.0, -85.0, "North America interior"),
    "jpn": (30.0, 46.0, 128.0, 146.0, "Japan convergent margin"),
}


def export_region(
    frame: str,
    region: str,
    out_path: str,
    gnss_cache: str = "data/raw/gnss",
    max_stations: int = 2000,
) -> dict:
    path = os.path.join(gnss_cache, f"midas.{frame}.txt")
    field = parse_midas(open(path).read(), frame=frame).eligible(5.0)
    a = field.arrays()
    lat, lon, vel, cov = a["lat"], a["lon"], a["vel_en"], a["cov_en"]
    lo_lat, hi_lat, lo_lon, hi_lon, label = REGION_BOXES[region]
    m = (lat > lo_lat) & (lat < hi_lat) & (lon > lo_lon) & (lon < hi_lon)
    idx = np.where(m)[0]
    if idx.size > max_stations:
        idx = idx[np.linspace(0, idx.size - 1, max_stations).astype(int)]
    lat, lon, vel, cov = lat[idx], lon[idx], vel[idx], cov[idx]

    fit = fit_euler_pole(lat, lon, vel, cov)
    rigid = RigidOnly(omega=fit.omega)
    rigid_pred = rigid.predict(lat, lon)
    local = LocalRegression.fit(lat, lon, vel, cov, bandwidth_deg=1.5)
    local_pred = local.predict(lat, lon)

    folds = spatial_block_folds(lat, lon, n_folds=5, buffer_deg=0.3, seed=0)
    fold_of = np.full(lat.size, -1)
    for fi, f in enumerate(folds):
        fold_of[f.test_idx] = fi

    stations = []
    for i in range(lat.size):
        stations.append({
            "lat": float(lat[i]), "lon": float(lon[i]),
            "obs_e": float(vel[i, 0]), "obs_n": float(vel[i, 1]),
            "sig_e": float(np.sqrt(cov[i, 0, 0])), "sig_n": float(np.sqrt(cov[i, 1, 1])),
            "rigid_e": float(rigid_pred[i, 0]), "rigid_n": float(rigid_pred[i, 1]),
            "local_e": float(local_pred[i, 0]), "local_n": float(local_pred[i, 1]),
            "fold": int(fold_of[i]),
        })

    payload = {
        "frame": frame,
        "region": region,
        "region_label": label,
        "source": field.source,
        "citation": field.citation,
        "n_stations": len(stations),
        "rigid_pole": {"lat": fit.pole_lat_deg, "lon": fit.pole_lon_deg, "rate_deg_myr": fit.rate_deg_per_myr},
        "units": "mm/yr",
        "stations": stations,
    }
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, "w") as fh:
        json.dump(payload, fh)
    return {"out": out_path, "n": len(stations), "region": label}


def main(argv=None):
    import argparse

    p = argparse.ArgumentParser(prog="lithora-export-web")
    p.add_argument("--frame", default="IGS14")
    p.add_argument("--region", default="cal")
    p.add_argument("--out", required=True)
    p.add_argument("--max-stations", type=int, default=2000)
    args = p.parse_args(argv)
    print(json.dumps(export_region(args.frame, args.region, args.out, max_stations=args.max_stations), indent=2))


if __name__ == "__main__":
    main()
