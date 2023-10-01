# 1. Rust for the kinematics core

## Context

The reconstruction and velocity math must be exact to tight tolerances, fast
enough to tile a globe, and free of hidden numerical behaviour from a large
dependency. It is also the part most likely to be wrong in subtle ways
(composition order, units, small-angle precision).

## Decision

Implement the geometry and kinematics core in Rust as a dependency-light crate
(`lithora-geo` depends only on `serde` and `thiserror`).

## Alternatives

- Pure Python/NumPy: simplest, but slower for per-point tiling and more prone
  to silent float coercion across array operations.
- C++: comparable performance, but weaker safety guarantees and a heavier build.

## Consequences

Strong compile-time guarantees and good performance, at the cost of a second
language in the project. The Python layer must not reimplement this engine; it
consumes the same conventions. The split is a feature: the authoritative math
has one home.
