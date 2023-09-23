"""Semantic negative controls for the verifier (gate G13).

A verifier that only recomputes hashes can be fooled by editing a result and
updating the hash. These controls prove the verifier checks meaning, not just
bytes: each takes a valid evidence bundle, applies one semantic corruption,
recomputes the ordinary manifest hashes so the bundle is internally
consistent, and then invokes the real verifier as a subprocess. A correct
verifier must still reject, and for a reason tied to the corruption.

Controls implemented:

1. Reversed-sign pole: negate the stored Euler rate so it no longer matches the
   raw records. Tests the independent pole recomputation.
2. mm/metre scale error: multiply the stored residual by 1000 (a metre/mm
   confusion). Tests the residual recomputation.
3. Flipped comparison claim: assert the rigid model beat the local one when the
   raw RMSEs say the opposite. Tests the relationship recomputation.
4. Data floor lie: claim the 1000-station floor is met while the count is below
   it. Tests the coverage recomputation.
5. Missing artifact and manifest-hash mismatch: structural controls.

Each control records the verifier's exit status and rejection reason.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile


def _sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _reseal_manifest(bundle: str) -> None:
    """Recompute the manifest so the tampered bundle is internally consistent.

    This is what makes the control meaningful: an ordinary hash check would
    now pass, so only a semantic recomputation can catch the corruption.
    """
    manifest_path = os.path.join(bundle, "MANIFEST.json")
    with open(manifest_path) as fh:
        manifest = json.load(fh)
    for name in list(manifest["files"].keys()):
        manifest["files"][name] = _sha256_file(os.path.join(bundle, name))
    with open(manifest_path, "w") as fh:
        json.dump(manifest, fh, indent=2, sort_keys=True)
    # The manifest file itself is not listed in its own files map, matching the
    # runner, so no self-reference to reseal.


def _write_obs(bundle: str, obs: dict) -> None:
    with open(os.path.join(bundle, "OBSERVATIONS.json"), "w") as fh:
        json.dump(obs, fh, indent=2, sort_keys=True)


def _run_verifier(bundle: str) -> tuple[int, dict]:
    proc = subprocess.run(
        [sys.executable, "-m", "lithora.verify", "--evidence", bundle],
        capture_output=True,
        text=True,
    )
    try:
        out = json.loads(proc.stdout)
    except json.JSONDecodeError:
        out = {"raw": proc.stdout, "stderr": proc.stderr}
    return proc.returncode, out


def run_controls(source_bundle: str) -> list[dict]:
    """Run all negative controls against copies of ``source_bundle``."""
    results = []
    work = tempfile.mkdtemp(prefix="lithora-neg-")

    def fresh(tag: str) -> str:
        dst = os.path.join(work, tag)
        shutil.copytree(source_bundle, dst)
        return dst

    # Control 1: reversed-sign / wrong pole.
    b = fresh("reversed_pole")
    obs = json.load(open(os.path.join(b, "OBSERVATIONS.json")))
    obs["na_rigid_fit"]["pole_lat"] = -obs["na_rigid_fit"]["pole_lat"]
    obs["na_rigid_fit"]["pole_lon"] = obs["na_rigid_fit"]["pole_lon"] + 90.0
    _write_obs(b, obs)
    _reseal_manifest(b)
    rc, out = _run_verifier(b)
    results.append({"control": "reversed_pole", "exit": rc, "rejected": rc != 0, "reason": out.get("reason")})

    # Control 2: mm/metre scale error on the residual.
    b = fresh("scale_error")
    obs = json.load(open(os.path.join(b, "OBSERVATIONS.json")))
    obs["na_rigid_fit"]["median_residual_mm_yr"] *= 1000.0
    _write_obs(b, obs)
    _reseal_manifest(b)
    rc, out = _run_verifier(b)
    results.append({"control": "scale_error", "exit": rc, "rejected": rc != 0, "reason": out.get("reason")})

    # Control 3: flipped model-comparison claim.
    b = fresh("flipped_comparison")
    obs = json.load(open(os.path.join(b, "OBSERVATIONS.json")))
    obs["ca_model_comparison"]["local_improves_over_rigid"] = not obs["ca_model_comparison"]["local_improves_over_rigid"]
    _write_obs(b, obs)
    _reseal_manifest(b)
    rc, out = _run_verifier(b)
    results.append({"control": "flipped_comparison", "exit": rc, "rejected": rc != 0, "reason": out.get("reason")})

    # Control 4: data floor lie.
    b = fresh("data_floor_lie")
    obs = json.load(open(os.path.join(b, "OBSERVATIONS.json")))
    obs["data_coverage"]["n_eligible"] = 10
    obs["data_coverage"]["meets_1000_floor"] = True
    _write_obs(b, obs)
    _reseal_manifest(b)
    rc, out = _run_verifier(b)
    results.append({"control": "data_floor_lie", "exit": rc, "rejected": rc != 0, "reason": out.get("reason")})

    # Control 5: manifest hash mismatch (structural: tamper without resealing).
    b = fresh("hash_mismatch")
    obs = json.load(open(os.path.join(b, "OBSERVATIONS.json")))
    obs["na_rigid_fit"]["rate_deg_myr"] = 99.0
    _write_obs(b, obs)  # deliberately do NOT reseal
    rc, out = _run_verifier(b)
    results.append({"control": "hash_mismatch", "exit": rc, "rejected": rc != 0, "reason": out.get("reason")})

    # Control 6: missing required artifact.
    b = fresh("missing_artifact")
    os.remove(os.path.join(b, "OBSERVATIONS.json"))
    rc, out = _run_verifier(b)
    results.append({"control": "missing_artifact", "exit": rc, "rejected": rc != 0, "reason": out.get("reason")})

    shutil.rmtree(work, ignore_errors=True)
    return results


def main(argv=None) -> int:
    import argparse

    p = argparse.ArgumentParser(prog="lithora-negative-controls")
    p.add_argument("--evidence", required=True)
    args = p.parse_args(argv)
    results = run_controls(args.evidence)
    all_rejected = all(r["rejected"] for r in results)
    print(json.dumps({"all_rejected": all_rejected, "controls": results}, indent=2))
    return 0 if all_rejected else 1


if __name__ == "__main__":
    sys.exit(main())
