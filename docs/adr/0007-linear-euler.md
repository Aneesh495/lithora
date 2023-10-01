# 7. Linear weighted least squares for the Euler pole

## Context

The rigid inverse problem estimates one Euler vector from station velocities.

## Decision

Solve it as a weighted linear least squares, exploiting that `v = omega x r` is
linear in `omega`, and derive the covariance from the weighted normal matrix.

## Alternatives

- Nonlinear optimisation over pole lat/lon/rate: unnecessary, since the problem
  is linear in the Euler vector; it only adds local minima and convergence
  worries.
- Unweighted least squares: ignores known per-station velocity uncertainty.

## Consequences

A direct, robust estimate with an analytic covariance and an explicit condition
number that flags poorly constrained axes. A singular per-station covariance
(for example zero-noise synthetic data) degrades to an identity weight rather
than crashing, with that behaviour documented.
