# Benchmark methodology

## What is measured

`make bench` runs `crates/lithora-geo/benches/reconstruct_throughput.rs`, a
plain binary (not a statistical harness) that times the hot paths of the core:
rotation application, rotation composition, and spherical polygon containment.
It reports iterations per second after a warm-up and asserts loose floors that
catch a catastrophic regression without being flaky on a loaded machine.

## Why not a micro-benchmark framework

A full framework (criterion) gives confidence intervals but adds a dependency
and build time to an otherwise minimal core. For the purpose here, detecting
large regressions and sizing the tiling budget, a warm-up plus a fixed
iteration count with `black_box` to defeat dead-code elimination is sufficient
and transparent. If statistical rigor becomes necessary, criterion can be added
behind a feature.

## How to read the numbers

Throughput is machine and build dependent; always run with `--release`
(the Makefile target does). Report numbers alongside the host. On the
development host (Apple Silicon, release build) the core measured roughly:

| Path | Throughput |
|---|---|
| rotation apply | about 2.0e8 /s |
| rotation compose | about 2.1e8 /s |
| polygon contains (4 vertices) | about 5.8e6 /s |

At those rates a 10,000-station velocity tile costs well under a millisecond of
rotation work, so the reconstruction core is not the bottleneck for interactive
globe tiling; rendering and data transfer dominate.

## Resource behaviour

The bounded tile cache (`crates/lithora-recon/src/cache.rs`) is the mechanism
that keeps a long mixed-query session within memory: LRU eviction holds the
entry count at the configured capacity, and the generation guard prevents a
superseded computation from polluting the cache. The full 12-hour mixed-query
stress run (gate G12) is declared in `docs/EXPERIMENT_PLAN.md` and uses this
cache; the diagnostic profile exercises the eviction and generation logic
through the unit tests.
