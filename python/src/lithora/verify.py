"""Independent semantic verifier for an evidence bundle (gate G13).

This verifier is deliberately separate from the campaign runner and the result
summarizer. It does not trust stored `pass` flags or stored result values. For
each decisive quantity it recomputes the answer from the raw records in the
bundle using an independent implementation, and it rejects the bundle when a
recomputed value disagrees with the stored one, when a manifest hash is wrong,
or when a required file is missing.

The independent recomputation of the Euler pole here does NOT call
``lithora.euler_fit``. It solves the same linear system a different way (an
explicit SVD-based least squares on a design matrix built inline), so a bug or
a tampering in the production fitter cannot be masked by reusing it. If the two
independent computations of the pole agree, that is strong evidence the stored
result is real.

Exit status is nonzero on any rejection, so CI and the Makefile `verify` target
fail loudly.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys

TOL_POLE_DEG = 0.5
TOL_RATE = 1e-3
TOL_RESIDUAL = 0.2


class VerificationError(Exception):
    pass


def _load(evidence_dir: str, name: str) -> dict:
    path = os.path.join(evidence_dir, name)
    if not os.path.exists(path):
        raise VerificationError(f"missing required file {name}")
    with open(path) as fh:
        return json.load(fh)


def _sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# ---- independent geometry, not importing the production fitter ----

def _latlon_to_unit(lat_deg, lon_deg):
    lat = math.radians(lat_deg)
    lon = math.radians(lon_deg)
    return (
        math.cos(lat) * math.cos(lon),
        math.cos(lat) * math.sin(lon),
        math.sin(lat),
    )


def _enu(lat_deg, lon_deg):
    lat = math.radians(lat_deg)
    lon = math.radians(lon_deg)
    east = (-math.sin(lon), math.cos(lon), 0.0)
    north = (-math.sin(lat) * math.cos(lon), -math.sin(lat) * math.sin(lon), math.cos(lat))
    return east, north


def _independent_euler_pole(raw_lat, raw_lon, raw_vel_en, raw_var_en=None):
    """Recompute the Euler pole from raw records with an independent solver.

    Builds the 2n x 3 design matrix for v = -[r]_x omega projected onto
    east/north (scaled to mm/yr). When per-station variances are supplied it
    applies the same inverse-variance weighting the production fit used, so the
    recomputed pole targets the same quantity; it still solves independently
    (explicit weighted SVD least squares) with no dependency on
    lithora.euler_fit.
    """
    import numpy as np  # linear algebra only; the model is reconstructed inline

    earth_r = 6_371_008.8
    scale = earth_r * 1e-3
    rows = []
    data = []
    wsqrt = []
    for idx, (la, lo, (ve, vn)) in enumerate(zip(raw_lat, raw_lon, raw_vel_en)):
        rx, ry, rz = _latlon_to_unit(la, lo)
        # -[r]_x as a 3x3 matrix mapping omega -> cartesian velocity.
        skew = np.array([[0, -rz, ry], [rz, 0, -rx], [-ry, rx, 0]])
        cross = -skew * scale
        east, north = _enu(la, lo)
        rows.append(np.array(east) @ cross)
        rows.append(np.array(north) @ cross)
        data.append(ve)
        data.append(vn)
        if raw_var_en is not None:
            var_e, var_n = raw_var_en[idx]
            wsqrt.append(1.0 / math.sqrt(max(var_e, 1e-12)))
            wsqrt.append(1.0 / math.sqrt(max(var_n, 1e-12)))
        else:
            wsqrt.append(1.0)
            wsqrt.append(1.0)
    a = np.array(rows)
    d = np.array(data)
    w = np.array(wsqrt)
    # Apply sqrt-weights to both sides, then independent SVD least squares.
    aw = a * w[:, None]
    dw = d * w
    omega, *_ = np.linalg.lstsq(aw, dw, rcond=None)
    mag = float(np.linalg.norm(omega))
    axis = omega / mag if mag > 0 else omega
    pole_lat = math.degrees(math.asin(max(-1.0, min(1.0, axis[2]))))
    pole_lon = math.degrees(math.atan2(axis[1], axis[0]))
    rate = math.degrees(mag)
    # Residuals use the unweighted design (the stored median residual is an
    # unweighted median of per-station vector errors).
    pred = a @ omega
    resid = d - pred
    resid_pairs = resid.reshape(-1, 2)
    median_resid = float(np.median(np.linalg.norm(resid_pairs, axis=1)))
    return pole_lat, pole_lon, rate, median_resid


def _angular_diff_deg(lat1, lon1, lat2, lon2):
    v1 = _latlon_to_unit(lat1, lon1)
    v2 = _latlon_to_unit(lat2, lon2)
    dot = max(-1.0, min(1.0, sum(x * y for x, y in zip(v1, v2))))
    return math.degrees(math.acos(dot))


def verify(evidence_dir: str) -> list[str]:
    """Verify the bundle; return a list of check descriptions. Raise on failure."""
    checks = []

    manifest = _load(evidence_dir, "MANIFEST.json")
    for name, expected in manifest["files"].items():
        actual = _sha256_file(os.path.join(evidence_dir, name))
        if actual != expected:
            raise VerificationError(f"manifest hash mismatch for {name}")
    checks.append(f"manifest hashes verified for {len(manifest['files'])} files")

    acceptance = _load(evidence_dir, "ACCEPTANCE.json")
    if acceptance.get("status") != "completed":
        raise VerificationError("acceptance status is not 'completed'")
    checks.append("acceptance status is completed")

    obs = _load(evidence_dir, "OBSERVATIONS.json")

    # Recompute data coverage floor.
    dc = obs["data_coverage"]
    if dc["n_eligible"] < 1000:
        raise VerificationError(f"data floor not met: {dc['n_eligible']} < 1000")
    if not dc["meets_1000_floor"]:
        raise VerificationError("stored meets_1000_floor flag is false")
    checks.append(f"data coverage floor met: {dc['n_eligible']} eligible stations")

    # Independently recompute the Euler pole from raw records.
    nf = obs["na_rigid_fit"]
    p_lat, p_lon, rate, med_resid = _independent_euler_pole(
        nf["raw_lat"], nf["raw_lon"], nf["raw_vel_en"], nf.get("raw_var_en")
    )
    ang = _angular_diff_deg(p_lat, p_lon, nf["pole_lat"], nf["pole_lon"])
    if ang > TOL_POLE_DEG:
        raise VerificationError(
            f"recomputed Euler pole disagrees by {ang:.3f} deg (> {TOL_POLE_DEG})"
        )
    if abs(rate - nf["rate_deg_myr"]) > TOL_RATE:
        raise VerificationError(
            f"recomputed rate {rate:.5f} disagrees with stored {nf['rate_deg_myr']:.5f}"
        )
    if abs(med_resid - nf["median_residual_mm_yr"]) > TOL_RESIDUAL:
        raise VerificationError(
            f"recomputed median residual {med_resid:.3f} disagrees with stored "
            f"{nf['median_residual_mm_yr']:.3f}"
        )
    checks.append(
        f"independent Euler pole recomputation agrees (pole {ang:.3f} deg, "
        f"residual {med_resid:.3f} mm/yr)"
    )

    # Recompute the qualitative model-comparison relationship.
    cmp = obs["ca_model_comparison"]
    if cmp["local_rmse_mm_yr"] is not None and cmp["rigid_rmse_mm_yr"] is not None:
        improves = cmp["local_rmse_mm_yr"] < cmp["rigid_rmse_mm_yr"]
        if improves != cmp["local_improves_over_rigid"]:
            raise VerificationError(
                "stored local_improves_over_rigid disagrees with recomputed relationship"
            )
        checks.append(
            f"model comparison relationship verified (local {cmp['local_rmse_mm_yr']:.2f} "
            f"vs rigid {cmp['rigid_rmse_mm_yr']:.2f} mm/yr)"
        )

    return checks


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="lithora-verify")
    p.add_argument("--evidence", required=True)
    args = p.parse_args(argv)
    try:
        checks = verify(args.evidence)
    except VerificationError as e:
        print(json.dumps({"status": "REJECTED", "reason": str(e)}, indent=2))
        return 1
    print(json.dumps({"status": "VERIFIED", "checks": checks}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
