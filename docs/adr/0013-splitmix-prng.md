# 13. SplitMix64 for reproducible property tests

## Context

The gate-G01 geometry campaign needs hundreds of thousands of reproducible
random cases, and a failing case must be replayable exactly.

## Decision

Implement a small SplitMix64 generator in the Rust core's test utilities rather
than pulling in an external RNG crate.

## Alternatives

- The `rand` crate: fine, but adds a dependency to a core that is otherwise
  deliberately minimal, and pins its own version churn.
- The standard library: has no portable seeded float generator.

## Consequences

Reproducible seeded sampling of rotations, sphere points, and unit vectors with
no dependency, so any failing property case is replayable from its seed. The
generator is compiled only for tests, so it is not part of the shipped
numerical surface. A test confirms the sequence is reproducible from a seed and
roughly uniform.
