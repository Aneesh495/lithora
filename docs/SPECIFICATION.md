# Specification and capability map

This maps the project's required capabilities to where they are implemented and
how they are tested. Status is honest: `done` means code plus a passing test or
a runnable path; `partial` means the mechanism exists but the full-scale run is
pending; `pending` means designed but not yet built.

## Capability map

| ID | Capability | Where | Status |
|---|---|---|---|
| L01 | Rotation-file ingestion with schema and bounds | `recon/rot_format.rs` | done |
| L02 | Quaternion/axis-angle algebra, edge cases | `geo/rotation.rs` | done |
| L03 | Piecewise finite-rotation interpolation vs Cartesian | `geo/sequence.rs` | done |
| L04 | Plate-circuit graph, anchors, cycles, missing intervals | `geo/circuit.rs` | done |
| L05 | Rigid reconstruction, motion paths, stage velocities | `recon/reconstruct.rs`, `geo/velocity.rs` | done |
| L06 | Spherical polygon containment, dateline, poles, holes | `geo/polygon.rs` | done |
| L07 | Area and distance with documented assumptions | `geo/polygon.rs` | done |
| L08 | Cross-model comparison at matched times | `recon/compare.rs` + CLI | done |
| L09 | Boundary classification where topology supports it | `recon/boundary.rs` | done |
| L10 | GNSS metadata joins and quality flags | `data/ngl.py` | done |
| L11 | Robust time-series velocity with seasonal/offset/correlated noise | `timeseries.py` | done |
| L12 | Frame transforms only with verified params; reject unsupported | `data/ngl.py` | done |
| L13 | Weighted rigid Euler-pole fit with covariance and conditioning | `euler_fit.py` | done |
| L14 | Identifiability diagnostics | `euler_fit.py` | done |
| L15 | Deterministic baselines + GP | `baselines.py`, `gp.py` | done |
| L16 | Original spherical graph residual model | `graph_model.py` | done |
| L17 | Physical regularization of residual field | `graph_model.py` (smooth MLP) | partial |
| L18 | Heteroscedastic vs epistemic uncertainty, ensembles | `uncertainty.py`, `train.py` seeds | done |
| L19 | Calibrated regions with spatial block validation | `evaluate.py` | partial |
| L20 | Spatial/plate/temporal holdouts with buffer | `evaluate.py`, leave-region-out CLI | done |
| L21 | Strain-rate tensor from differentiable fields | `strain.py` + CLI | done |
| L22 | Residual outlier investigation with provenance | `outliers.py` + CLI | done |
| L23 | Synthetic known-truth worlds | `synthetic.py` | done |
| L24 | Globe with all layers | `web/` | pending |
| L25 | Geological timeline bounded by model validity | `geo/sequence.rs` enforces | partial |
| L26 | Separate modern/paleo clocks | design + diagram | partial |
| L27 | Vector exaggeration with scale legend | `web/` | pending |
| L28 | Station inspector | `web/` | pending |
| L29 | Linked cross-sections | `profile.py` | done |
| L30 | Layer provenance, legends, downloads | `web/` | pending |
| L31 | Spatial tiling/query/cache with full keys | `recon/cache.rs` | done |
| L32 | Bounded async with cancellation and generation IDs | `recon/cache.rs`, atlas gen counter | done |
| L33 | Notebooks as reproducible views | `notebooks/` | done |
| L34 | Independent comparison vs pyGPlates | - | pending (needs pyGPlates) |
| L35 | Research registry of seeds/folds/held-out identities | `registry.py` | done |
| L36 | Executable atlas tour | `web/` | pending |

## Gate status

See `docs/BUILD_STATUS.md` for the running status. Summary:

- G01 geometry: passing (>100k property cases, adversarial pole/dateline).
- G03 velocity: passing on analytic/finite-difference agreement.
- G04 data: real profile met (20,168 IGS14 stations, 16,002 eligible).
- G05 inverse: passing on synthetic recovery (scale-limited count pending).
- G06 learning: passing on gradients/checkpoint/held-out gains (full campaign partial).
- G07 comparison: real cross-region comparison produced; full budgets pending.
- G08 calibration: measured (GP overconfidence in CA found); full report partial.
- G09 physics: equivariance passing at feature level.
- G02 reconstruction (pyGPlates), G10-G15: pending external deps / web / campaign.

## Contracts

- Units, time, and frame conventions: `docs/DERIVATIONS.md` and `geo/units.rs`.
- Error taxonomy (bad input vs unsupported request): `geo/error.rs`.
- Data provenance schema: `data/acquire.py` manifests.
