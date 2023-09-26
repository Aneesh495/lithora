# Experiment plan

This plan is frozen before final measurements. It separates the CPU diagnostic
profile (fast, runs in CI and on a laptop) from the full acceptance profile
(many folds and seeds, heavier compute). A change to a threshold or workload
after seeing results requires a new version of this document and a new
campaign; earlier results are retained, not overwritten.

## Hypotheses and endpoints

- H1 (residual benefit, region dependent): a learned or local residual model
  reduces held-out vector RMSE relative to rigid-only in a deforming margin,
  but not in a rigid interior. Decision: paired per-fold RMSE, residual model
  wins in >= 4 of 5 folds in the deforming region and does not significantly
  beat rigid in the interior.
- H2 (coordinate consistency): rotating the station network in longitude
  leaves the graph model's tangent features unchanged and rotates its outputs
  correspondingly, within 1e-6 on the features. Decision: equivariance test
  passes.
- H3 (sparse-region uncertainty): the GP's interval coverage degrades (becomes
  overconfident) in strongly deforming or sparse regions relative to a dense
  rigid interior. Decision: report coverage by region; a drop below nominal is
  recorded as a calibration failure, not hidden.
- H4 (frame sensitivity): rigid-pole estimates differ between a global frame
  and a plate-fixed frame by a quantifiable amount; mixing frames is rejected.
- H5 (reconstruction model dependence): two published rotation models disagree
  on reconstructed positions at matched ages and anchors; the disagreement is
  shown, not averaged. (Pending two pinned models.)
- H6 (velocity recovery): synthetic Euler poles recover within the fit's
  covariance across many simulated datasets.
- H7 (training reality): gradients and parameters change, held-out inference
  improves over an untrained model with the same architecture.
- H8 (geometry tolerance): random rotation/containment invariants hold within
  declared tolerances over >= 100,000 cases.

Hypotheses may be disproved. H1 in the North America interior is expected to
show no residual benefit, and that negative result is a finding.

## Independent evaluation units

- Geometry: independent random cases (seeded) and adversarial pole/dateline.
- Inverse problem: independent synthetic worlds, one Euler vector each.
- Spatial prediction: spatially buffered folds; test stations never within the
  buffer of a training station.

## Tolerances

- G01 geometry: norm preservation 1e-12, angle recovery 1e-10, associativity
  1e-10.
- G02 reconstruction: 1e-7 rad vs independent reference for pure rigid points.
- G03 velocity: analytic vs finite-difference agreement 1e-7 for a 1e-4 Ma
  stage.
- G05 inverse: true omega within the 99% chi-square region in the large
  majority of simulated datasets.

## Seeds and profiles

- Learned comparisons use at least three independent training seeds per fold.
- CPU diagnostic profile: 5 folds, 1 region each, short training (<= 300
  epochs). Runs in CI.
- Full acceptance profile: 5+ buffered folds, 3 seeds per fold, one
  leave-region-out, full epochs, plus a 12-hour mixed-query stress run for
  resource behavior (G12). Declared here; run on suitable hardware.

## Resource ceilings

- Diagnostic profile is bounded to minutes and a few hundred MB.
- The exact GNSS input bytes are hashed in the evidence bundle; a source change
  invalidates affected final evidence.

## Exclusions from the code census

Tests, fixtures, benchmarks, docs, notebooks, generated bindings, vendored
trees, and downloaded data are excluded from the production line count. Shared
code is counted once.
