# 10. Independent verifier separate from the summarizer

## Context

An evidence bundle can be tampered with, and a verifier that only checks hashes
can be fooled by editing a result and re-hashing.

## Decision

Implement the verifier as a separate program that recomputes decisive
quantities from the raw records with an independent implementation (for the
Euler pole, a weighted SVD solve that does not import the production fitter),
and reject on semantic disagreement, not just hash mismatch.

## Alternatives

- Trust stored pass flags: defeats the purpose.
- Reuse the production fitter in the verifier: a bug or tampering in the fitter
  would be masked.

## Consequences

The verifier catches reversed poles, mm/metre scale errors, flipped comparison
claims, and data-floor lies, each proven by a negative control that re-seals
the manifest so only semantic recomputation can catch it. The cost is a second
independent implementation of the pole solve, which is exactly the point.
