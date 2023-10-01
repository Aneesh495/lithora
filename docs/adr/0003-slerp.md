# 3. Slerp for rotation interpolation

## Context

Reconstructing at an age between two sampled total reconstruction poles needs
interpolation.

## Decision

Spherical linear interpolation (slerp) of the bracketing quaternions.

## Alternatives

- Linear interpolation of reconstructed Cartesian points: wrong, because it
  cuts a chord through the sphere and the intermediate point leaves the
  surface.
- Higher-order quaternion splines (squad): smoother derivatives but more
  complex and not needed for piecewise-linear rotation models.

## Consequences

The interpolant stays on the rotation group and reconstructed points stay on
the sphere. A test compares the 90-degree-rotation slerp midpoint (a 45-degree
rotation) against the chord midpoint (norm about 0.707) to lock in the
distinction. Near-identical and antipodal quaternion pairs are handled by a
linear fallback and a sign flip respectively.
