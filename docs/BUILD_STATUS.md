# Build status

This file tracks what is actually built, tested, and verified in Lithora. It
is kept honest: a capability is only marked done when there is code plus a
passing test or a runnable demo behind it.

## Environment (verified 2026-11-02)

- Rust 1.88.0, Cargo 1.88.0
- Python 3.14.2 (numpy 2.5.4, scipy 1.18.1, pandas 3.0.6; no torch/pyarrow yet)
- Node 24.21.0
- Target host: Apple Silicon macOS (aarch64)

## Rust core (lithora-geo, lithora-recon, lithora-cli)

| Area | Status | Evidence |
|---|---|---|
| Units and conventions | done | `units` module + tests |
| Vec3 algebra | done | `vec3` module + tests |
| Geographic <-> sphere | done | `coord` module + tests |
| Quaternion finite rotations | done | `rotation` module + tests (identity, small-angle, antipodal, noncommuting) |
| Geodetic/geocentric ellipsoid | done | `ellipsoid` module + tests |
| Finite-rotation interpolation (slerp) | done | `sequence` module + tests (chord-vs-arc check) |
| Plate-circuit evaluation | done | `circuit` module + tests (chain, reanchor, cycle, missing path) |
| Angular/linear velocity | done | `velocity` module + tests (cross product vs finite-difference stage) |
| Spherical polygons | done | `polygon` module + tests (dateline, poles, holes, orientation) |
| `.rot` file parser | done | `rot_format` module + tests |
| Reconstruction orchestration | done | `reconstruct` module + tests |
| CLI with runnable demo | done | `lithora demo` |

Current test count: 64 Rust unit tests passing.

## Python inference layer (python/)

| Area | Status | Evidence |
|---|---|---|
| Sphere ops (numpy) | done | `sphere.py` + tests |
| Weighted Euler-pole fit | done | `euler_fit.py`, recovers synthetic within 5% |
| Synthetic known-truth worlds | done | `synthetic.py` |
| Deterministic baselines | done | `baselines.py` (rigid/NN/local) |
| GP residual baseline | done | `gp.py` with predictive std |
| Spatial buffered folds + metrics | done | `evaluate.py` + tests |
| Parallel transport / tangent frames | done | `transport.py` + tests |
| Spherical graph residual model | done | `graph_model.py` (PyTorch 2.15, MPS) |
| Training harness | done | `train.py`: gradients/checkpoint/held-out gains |
| Robust GNSS time-series fit | done | `timeseries.py` + tests |
| NGL + USGS acquisition | done | `data/` with provenance; 20,168 IGS14 stations pulled |

Current test count: 36 Python tests passing + 64 Rust unit + 11 Rust G01 = 111.

## Measured real-data result (integration check)

Rigid Euler-pole fit to 1,374 North American interior IGS14 stations:
median residual 0.44 mm/yr against a 15.4 mm/yr observed field, condition
number ~1e2, not rank deficient. A rigid interior collapsing the field to a
sub-mm residual is the expected behaviour and validates the fit on real data.

## Not yet built / blocked on external resources

- CesiumJS globe: planned under `web/`.
- pyGPlates differential verification (G02): needs pyGPlates install + models.
- Full multi-fold training campaign and 12-hour stress: harness exists; full
  run pending.
- Browser FPS benchmark (G11): pending the web globe.
- Reconstruction rotation models (EarthByte .rot for two published models):
  the parser and engine are done and tested on synthetic models; pinning two
  real published models with licenses is pending.

See `docs/SPECIFICATION.md` for the capability map and `docs/ARCHITECTURE.md`
for the system structure.
