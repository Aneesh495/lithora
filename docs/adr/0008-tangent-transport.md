# 8. Tangent-frame transport for the learned model

## Context

The learned residual model predicts tangent vectors on a sphere. A naive model
on raw lat/lon features learns coordinate artifacts that do not generalise.

## Decision

Express every vector in a local east/north frame and parallel-transport
neighbour vectors into the centre's frame before mixing; use only
rotation-invariant edge features.

## Alternatives

- Raw lat/lon and east/north features: lets the model key on absolute longitude
  and on the frame orientation, which a naive latitude/longitude baseline shows
  is a real artifact.
- Full SO(3)-equivariant network: more machinery than the 2D tangent problem
  needs.

## Consequences

The model is rotationally equivariant: a global longitude shift leaves its
inputs unchanged and rotates its outputs. A test confirms the tangent-frame edge
features are invariant to a 37-degree longitude shift. Only the message and
update weights are learned; the geometry is fixed.
