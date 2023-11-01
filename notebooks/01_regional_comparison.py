"""Reproducible view: regional model comparison on real GNSS data.

This reproduces the headline regional finding by calling the same package
functions the CLI and tests use. It prints a table comparing rigid-only against
the local and GP residual models across regions, using spatially buffered
folds. It is a view, not a source of truth: all computation lives in the
`lithora` package.

Run from the repository root after acquiring data:
    python notebooks/01_regional_comparison.py
"""

from __future__ import annotations

import os
import sys

import numpy as np

from lithora.baselines import LocalRegression, NearestNeighbor, RigidOnly
from lithora.data.ngl import parse_midas
from lithora.evaluate import spatial_block_folds, velocity_metrics
from lithora.gp import GPResidual

REGIONS = {
    "North America interior": (32, 49, -104, -85, 2.0),
    "California transform margin": (32, 42, -124, -114, 1.0),
}


def main() -> int:
    path = "data/raw/gnss/midas.IGS14.txt"
    if not os.path.exists(path):
        print("missing GNSS cache; run `make acquire-gnss` first", file=sys.stderr)
        return 2

    field = parse_midas(open(path).read(), frame="IGS14").eligible(5.0)
    a = field.arrays()
    lat, lon, vel, cov = a["lat"], a["lon"], a["vel_en"], a["cov_en"]

    print(f"{'region':30} {'n':>5} {'rigid':>7} {'nn':>7} {'local':>7} {'gp':>7}")
    for label, (lo_lat, hi_lat, lo_lon, hi_lon, bw) in REGIONS.items():
        m = (lat > lo_lat) & (lat < hi_lat) & (lon > lo_lon) & (lon < hi_lon)
        rl, rlon, rvel, rcov = lat[m], lon[m], vel[m], cov[m]
        folds = spatial_block_folds(rl, rlon, n_folds=5, buffer_deg=0.3, seed=0)
        acc = {k: [] for k in ["rigid", "nn", "local", "gp"]}
        for f in folds:
            if f.train_idx.size < 10 or f.test_idx.size < 1:
                continue
            tr, te = f.train_idx, f.test_idx
            models = {
                "rigid": RigidOnly.fit(rl[tr], rlon[tr], rvel[tr], rcov[tr]),
                "nn": NearestNeighbor.fit(rl[tr], rlon[tr], rvel[tr], rcov[tr]),
                "local": LocalRegression.fit(rl[tr], rlon[tr], rvel[tr], rcov[tr], bandwidth_deg=bw),
                "gp": GPResidual.fit(rl[tr], rlon[tr], rvel[tr], rcov[tr]),
            }
            for name, model in models.items():
                pred = model.predict(rl[te], rlon[te])
                acc[name].append(velocity_metrics(pred, rvel[te]).vector_rmse)
        means = {k: (np.mean(v) if v else float("nan")) for k, v in acc.items()}
        print(
            f"{label:30} {int(m.sum()):>5} "
            f"{means['rigid']:>7.2f} {means['nn']:>7.2f} "
            f"{means['local']:>7.2f} {means['gp']:>7.2f}"
        )
    print("\nUnits mm/yr. Lower is better. See docs/research/11_regional_deformation.md.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
