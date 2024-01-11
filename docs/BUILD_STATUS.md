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

Current test count: 122 Rust tests passing (unit + property + gate campaigns).

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

Current test count: 66 Python tests + 122 Rust tests = 188 total, all in CI.

Additional implemented modules since the first cut: strain-rate estimation
(L21), cross-model comparison (L08), boundary classification (L09), bounded
tile cache with generations (L31/L32), uncertainty budget (L18), residual
outlier investigation (L22), cross-section profiles (L29), research registry
(L35), plate assignment and quality flags (L06/L10), Vincenty geodesics (L07),
flowlines, and reproducible notebooks (L33).

## Measured real-data result (integration check)

Rigid Euler-pole fit to 1,374 North American interior IGS14 stations:
median residual 0.44 mm/yr against a 15.4 mm/yr observed field, condition
number ~1e2, not rank deficient. A rigid interior collapsing the field to a
sub-mm residual is the expected behaviour and validates the fit on real data.

## Atlas, verifier, and docs

| Area | Status | Evidence |
|---|---|---|
| CesiumJS globe | done | `web/`, builds with 0 type errors; screenshot `docs/atlas.png` |
| Web data export | done | `export_web.py`, real CA+NA samples committed |
| Acceptance runner | done | `acceptance.py`, writes evidence bundle |
| Independent verifier | done | `verify.py`, recomputes pole independently |
| Semantic negative controls | done | 6 controls, all reject correctly (G13) |
| Research notes | done | 12 notes in `docs/research/` with measured results |
| Diagrams | done | 13 Mermaid + rendered SVG in `docs/diagrams/` |
| ADRs | done | 13 in `docs/adr/` |
| CI workflow | done | `.github/workflows/ci.yml` (fmt, clippy -D, tests, build) |
| Multi-seed training | done | 3 seeds on real CA data (see research note 11) |

## Not yet built / blocked on external resources

- pyGPlates differential verification (G02): needs a pyGPlates install and two
  pinned published models. The engine and comparison machinery are built and
  tested on synthetic models.
- Full acceptance profile (many folds x 3 seeds x leave-region-out) and the
  12-hour stress run (G12): the diagnostic profile runs; the full campaign is
  declared in EXPERIMENT_PLAN and pending a longer run.
- Browser FPS benchmark at 10,000 glyphs on a pinned desktop (G11): the globe
  renders real data; the headless environment lacks a GPU/WebGL path and
  imagery tiles, so a measured FPS number needs a real desktop browser.
- Two pinned EarthByte rotation models with licenses (for G02/L08 at scale).

See `docs/SPECIFICATION.md` for the capability map and `docs/ARCHITECTURE.md`
for the system structure.
