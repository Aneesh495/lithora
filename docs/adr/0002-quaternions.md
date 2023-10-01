# 2. Unit quaternions for finite rotations

## Context

Plate reconstruction composes many finite rotations, including very small stage
angles and rotations near 180 degrees.

## Decision

Represent rotations as unit quaternions and apply them with the matrix-free
sandwich form.

## Alternatives

- Rotation matrices: intuitive but accumulate orthogonality drift under
  repeated composition and lose precision for tiny angles built from cos/sin.
- Euler angles: gimbal lock and ambiguous conventions, unacceptable for a
  circuit of arbitrary rotations.

## Consequences

Stable composition, exact identity and small-angle behaviour, and explicit
non-commutativity. The `q`/`-q` double cover is handled by canonicalising to
`w >= 0` for comparison. The `then` method encodes temporal order so call sites
do not have to remember the reversed multiplication.
