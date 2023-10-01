# 6. Reference frame as a typed, non-mergeable attribute

## Context

GNSS velocities are only meaningful in a stated reference frame, and mixing
frames produces silent nonsense.

## Decision

Carry the frame on the velocity field as a first-class attribute, record it in
the acquisition provenance, and make the merge function refuse to combine
fields with different frames.

## Alternatives

- Track the frame in documentation only: relies on discipline and fails
  silently when violated.
- Auto-convert between frames: only valid with verified published parameters
  and epochs, which are not always available; doing it implicitly would invent
  data.

## Consequences

A frame mismatch is a loud error, not a subtle wrong answer. Conversions are
allowed only with verified parameters; otherwise the frames stay separate. This
is capability L12 enforced in code.
