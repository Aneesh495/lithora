# Lithora research notes

These notes are the scientific writeup of what Lithora measures and what it
cannot. They are built on the real code and the real runs recorded in the
evidence bundles, and they keep the modern-geodesy and ancient-reconstruction
questions separate throughout.

Every number in these notes traces to a command you can rerun. Where a result
is a negative finding or a limitation, it is reported as such rather than
smoothed over.

## Index

- `01_reference_frames.md` -- what a reference frame is and why mixing them is
  rejected.
- `02_gnss_trend_noise.md` -- robust velocity estimation and correlated noise.
- `03_robust_euler_poles.md` -- the rigid inverse problem and conditioning.
- `04_plate_circuits.md` -- composition order, anchors, and discontinuities.
- `05_stage_velocities.md` -- finite vs stage rotations and v = omega x r.
- `06_spherical_polygons.md` -- containment on the sphere and its pitfalls.
- `07_reconstruction_disagreement.md` -- model disagreement as evidence.
- `08_spatial_splits.md` -- buffered folds and leakage.
- `09_vector_graph_learning.md` -- the residual model and equivariance.
- `10_uncertainty_calibration.md` -- where intervals hold and where they fail.
- `11_regional_deformation.md` -- interior vs margin case studies.
- `12_atlas_time_scale.md` -- dual clocks and exaggeration semantics.

## Frozen hypotheses

See `docs/EXPERIMENT_PLAN.md` for the eight frozen hypotheses (H1-H8). The
headline finding so far, on real IGS14 data:

- In the North America interior a single rigid Euler pole explains the field to
  a 0.44 mm/yr median residual, and no residual model improves held-out
  prediction there. The null hypothesis wins, as it should in a rigid interior.
- On the California transform margin a distance-weighted local model cuts
  held-out vector RMSE from about 14.8 (rigid) to 6.4 mm/yr, and the Gaussian
  process is visibly overconfident (1-sigma coverage about 0.09), a measured
  calibration failure under strong spatial structure.
- The learned spherical graph model beats rigid on held-out stations in two of
  three seeds (mean held-out RMSE about 12.4 vs 12.9 mm/yr) but with real
  seed-to-seed variance, and it does not beat the simpler local model at this
  network scale. Added complexity is not automatically justified.

## Reproduction

```
make bootstrap
make acquire-gnss
python -m lithora.cli fit-plates --frame IGS14 --region na
python -m lithora.cli spatial-evaluate --frame IGS14 --region cal
python -m lithora.cli train --frame IGS14 --region cal --seed 0
```
