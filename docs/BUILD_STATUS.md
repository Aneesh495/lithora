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

## Not yet built / blocked on external resources

- Real GNSS acquisition (>=1000 stations): blocked on network archive download.
- PyTorch learning stack: Python 3.14 has no torch wheels yet; the learning
  layer is designed to gate on availability.
- CesiumJS globe: planned under `web/`.
- pyGPlates differential verification (G02): needs pyGPlates install + models.
- Full acceptance campaign, 12-hour stress, browser FPS benchmark: pending.

See `docs/SPECIFICATION.md` for the capability map and `docs/ARCHITECTURE.md`
for the system structure.
