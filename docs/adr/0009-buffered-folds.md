# 9. Spatially buffered folds for evaluation

## Context

Spatial velocity fields are strongly autocorrelated, so ordinary random
cross-validation lets a test station be predicted by a near-identical training
neighbour and overstates accuracy.

## Decision

Partition into spatial blocks and, per fold, drop training stations within a
buffer distance of any test station.

## Alternatives

- Random k-fold: leaks adjacent stations across the split.
- Single train/test geographic split: one split has high variance and no
  per-fold uncertainty.

## Consequences

Honest generalisation estimates and a basis for calibration claims. Absolute
RMSE rises because easy near-neighbours are removed, so comparisons are made as
paired differences across models on identical folds. A test verifies no training
station lies within the buffer of any test station.
