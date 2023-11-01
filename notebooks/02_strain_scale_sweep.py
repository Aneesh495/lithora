"""Reproducible view: strain rate versus smoothing scale at a point.

Inferred strain rate depends on the smoothing scale, and this view makes that
dependence explicit by sweeping the scale at a point in the California shear
zone. All computation is in `lithora.strain`.

Run from the repository root after acquiring data:
    python notebooks/02_strain_scale_sweep.py
"""

from __future__ import annotations

import os
import sys

import numpy as np

from lithora.data.ngl import parse_midas
from lithora.strain import strain_scale_sweep


def main() -> int:
    path = "data/raw/gnss/midas.IGS14.txt"
    if not os.path.exists(path):
        print("missing GNSS cache; run `make acquire-gnss` first", file=sys.stderr)
        return 2

    field = parse_midas(open(path).read(), frame="IGS14").eligible(5.0)
    a = field.arrays()
    lat, lon, vel = a["lat"], a["lon"], a["vel_en"]

    # A point in the central California shear zone.
    q_lat, q_lon = 36.0, -120.5
    # Restrict to a local window for speed; the function weights by distance
    # anyway, so this only bounds the work.
    near = (np.abs(lat - q_lat) < 3) & (np.abs(lon - q_lon) < 3)
    results = strain_scale_sweep(
        q_lat, q_lon, lat[near], lon[near], vel[near], scales_deg=[0.3, 0.5, 1.0, 1.5, 2.0]
    )

    print(f"Strain rate at ({q_lat} N, {q_lon} E), central California")
    print(f"{'scale_deg':>10} {'dilatation':>12} {'max_shear':>11} {'princ_az':>10} {'n_eff':>8}")
    for r in results:
        print(
            f"{r.smoothing_scale_deg:>10.2f} {r.dilatation:>12.2f} "
            f"{r.max_shear:>11.2f} {r.principal_angle_deg:>10.1f} {r.n_effective:>8.1f}"
        )
    print("\nStrain in nanostrain/yr. The result changes with the smoothing")
    print("scale, which is why the scale is always reported alongside it.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
