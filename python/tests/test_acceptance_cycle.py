"""End-to-end test of the acceptance -> verify -> controls cycle.

This builds a synthetic evidence bundle via the same writer the real campaign
uses (minus the network-dependent data step), runs the real verifier against
it, and runs the negative controls, so the full gate-G13 cycle is exercised in
CI without needing the GNSS cache.
"""

import hashlib
import json
import os

import numpy as np

from lithora.euler_fit import fit_euler_pole, predict_velocities
from lithora.negative_controls import run_controls
from lithora.synthetic import make_rigid_plate
from lithora.verify import verify


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _bundle(dirpath):
    world = make_rigid_plate(
        n_stations=1200, pole_lat_deg=48, pole_lon_deg=-120, rate_deg_per_myr=0.6,
        region_center=(40, -112), region_half_width_deg=12, noise_mm_yr=0.3, seed=6,
    )
    lat, lon, vel, cov = world.lat_deg, world.lon_deg, world.vel_en_mm_yr, world.cov_en_mm_yr
    fit = fit_euler_pole(lat, lon, vel, cov)
    resid = float(np.median(np.linalg.norm(predict_velocities(fit.omega, lat, lon) - vel, axis=1)))
    obs = {
        "data_coverage": {
            "n_eligible": int(lat.size), "lat_min": float(lat.min()), "lat_max": float(lat.max()),
            "lon_min": float(lon.min()), "lon_max": float(lon.max()), "meets_1000_floor": True,
        },
        "na_rigid_fit": {
            "n": int(lat.size), "pole_lat": fit.pole_lat_deg, "pole_lon": fit.pole_lon_deg,
            "rate_deg_myr": fit.rate_deg_per_myr, "condition_number": fit.condition_number,
            "median_residual_mm_yr": resid,
            "raw_lat": lat.tolist(), "raw_lon": lon.tolist(), "raw_vel_en": vel.tolist(),
            "raw_var_en": [[float(cov[i][0, 0]), float(cov[i][1, 1])] for i in range(lat.size)],
        },
        "ca_model_comparison": {
            "n_folds": 3, "rigid_rmse_mm_yr": 14.0, "local_rmse_mm_yr": 6.0,
            "local_improves_over_rigid": True,
        },
    }
    for name, payload in [
        ("ENVIRONMENT.json", {"python": "test"}),
        ("DATASETS.json", {"synthetic": True}),
        ("OBSERVATIONS.json", obs),
        ("ACCEPTANCE.json", {"status": "completed", "profile": "test"}),
    ]:
        json.dump(payload, open(os.path.join(dirpath, name), "w"), indent=2, sort_keys=True)
    manifest = {"files": {n: _sha256(os.path.join(dirpath, n))
                          for n in ["ENVIRONMENT.json", "DATASETS.json", "OBSERVATIONS.json", "ACCEPTANCE.json"]}}
    json.dump(manifest, open(os.path.join(dirpath, "MANIFEST.json"), "w"), indent=2, sort_keys=True)


def test_full_cycle_verifies_and_controls_reject(tmp_path):
    bundle = str(tmp_path)
    _bundle(bundle)

    # The verifier accepts a valid bundle.
    checks = verify(bundle)
    assert len(checks) >= 4

    # Every negative control rejects.
    results = run_controls(bundle)
    assert len(results) == 6
    assert all(r["rejected"] for r in results), [r for r in results if not r["rejected"]]
