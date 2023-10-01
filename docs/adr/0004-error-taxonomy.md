# 4. Explicit error taxonomy: bad input versus unsupported request

## Context

Two very different situations arise: an input is malformed (a bad latitude, a
corrupt rotation line), or a well-formed request is simply not supported by the
available model (an age outside its interval, a missing circuit link).

## Decision

Give each its own error variant (`GeoError::InvalidCoord`, `Parse` for bad
input; `AgeOutOfRange`, `NoBracket`, `NoCircuitPath`, `CircuitCycle` for
unsupported requests).

## Alternatives

- One generic error: hides the difference between "fix your file" and "this
  model cannot answer that", which is exactly the geological-honesty line.
- Returning sentinel values (NaN, zero): silently fabricates plausible numbers.

## Consequences

Callers and the atlas can distinguish a user error from a genuine limit of the
model, and the system never extrapolates through an absent interval. The cost
is a slightly larger error enum, which is worth it.
