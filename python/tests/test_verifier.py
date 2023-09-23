"""Verifier and semantic negative controls (gate G13).

Builds a small synthetic evidence bundle (so the test needs no network), runs
the real verifier against it, and then runs every negative control to confirm
the verifier rejects each semantic corruption. This keeps the decisive gate-G13
behavior under continuous test rather than only in a one-off run.
"""

import hashlib
import json
import os

import numpy as np

from lithora.euler_fit import fit_euler_pole, predict_velocities
from lithora.negative_controls import run_controls
from lithora.synthetic import make_rigid_plate
from lithora.verify import VerificationError, verify


def _sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _build_bundle(tmp_path):
    # Synthetic network with >1000 stations so the coverage check passes.
    world = make_rigid_plate(
        n_stations=1100, pole_lat_deg=50, pole_lon_deg=-100, rate_deg_per_myr=0.7,
        region_center=(38, -110), region_half_width_deg=12, noise_mm_yr=0.3, seed=5,
    )
    lat, lon, vel, cov = world.lat_deg, world.lon_deg, world.vel_en_mm_yr, world.cov_en_mm_yr
    fit = fit_euler_pole(lat, lon, vel, cov)
    pred = predict_velocities(fit.omega, lat, lon)
    resid = float(np.median(np.linalg.norm(pred - vel, axis=1)))

    obs = {
        "data_coverage": {
            "n_eligible": int(lat.size),
            "lat_min": float(lat.min()), "lat_max": float(lat.max()),
            "lon_min": float(lon.min()), "lon_max": float(lon.max()),
            "meets_1000_floor": bool(lat.size >= 1000),
        },
        "na_rigid_fit": {
            "n": int(lat.size),
            "pole_lat": fit.pole_lat_deg, "pole_lon": fit.pole_lon_deg,
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
    d = str(tmp_path)
    for name, payload in [
        ("ENVIRONMENT.json", {"python": "test"}),
        ("DATASETS.json", {"synthetic": True}),
        ("OBSERVATIONS.json", obs),
        ("ACCEPTANCE.json", {"status": "completed", "profile": "test"}),
    ]:
        with open(os.path.join(d, name), "w") as fh:
            json.dump(payload, fh, indent=2, sort_keys=True)
    manifest = {"files": {}}
    for name in ["ENVIRONMENT.json", "DATASETS.json", "OBSERVATIONS.json", "ACCEPTANCE.json"]:
        manifest["files"][name] = _sha256_file(os.path.join(d, name))
    with open(os.path.join(d, "MANIFEST.json"), "w") as fh:
        json.dump(manifest, fh, indent=2, sort_keys=True)
    return d


def test_verifier_accepts_valid_bundle(tmp_path):
    bundle = _build_bundle(tmp_path)
    checks = verify(bundle)
    assert any("Euler pole recomputation agrees" in c for c in checks)
    assert any("floor met" in c for c in checks)


def test_all_negative_controls_rejected(tmp_path):
    bundle = _build_bundle(tmp_path)
    results = run_controls(bundle)
    assert len(results) == 6
    for r in results:
        assert r["rejected"], f"control {r['control']} was not rejected"


def test_verifier_rejects_tampered_pole(tmp_path):
    import pytest

    bundle = _build_bundle(tmp_path)
    obs = json.load(open(os.path.join(bundle, "OBSERVATIONS.json")))
    obs["na_rigid_fit"]["pole_lat"] = obs["na_rigid_fit"]["pole_lat"] + 40.0
    with open(os.path.join(bundle, "OBSERVATIONS.json"), "w") as fh:
        json.dump(obs, fh, indent=2, sort_keys=True)
    # Reseal manifest so only semantic recomputation can catch it.
    manifest = json.load(open(os.path.join(bundle, "MANIFEST.json")))
    manifest["files"]["OBSERVATIONS.json"] = _sha256_file(os.path.join(bundle, "OBSERVATIONS.json"))
    with open(os.path.join(bundle, "MANIFEST.json"), "w") as fh:
        json.dump(manifest, fh, indent=2, sort_keys=True)
    with pytest.raises(VerificationError, match="Euler pole"):
        verify(bundle)
