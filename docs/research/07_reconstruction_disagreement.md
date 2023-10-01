# Reconstruction disagreement

Two published rotation models reconstructing the same point at the same age and
anchor will generally not agree. That disagreement is evidence to investigate,
not a nuisance to average away.

## Why not average

Averaging two reconstructions into a single "best" position invents a truth
that neither model claims and hides the real uncertainty in deep-time plate
positions. Lithora's design keeps models separate and compares them only where
their topologies and age domains actually overlap. Where one model has no
topology for a time, that comparison is simply unavailable, not filled in.

## What a fair comparison requires

A fair cross-model comparison fixes the age, the anchor, and the point, then
reports the angular difference between the two reconstructed positions. Both
models must be evaluated through the same engine so the difference reflects the
models, not two different implementations. The gate-G02 tolerance of 1e-7
radians for pure rigid point reconstruction is about the engine agreeing with an
independent reference, which is a separate question from two geological models
disagreeing with each other.

## Current status

The engine and the comparison machinery are implemented and tested on synthetic
models. Pinning two real published EarthByte models with their licenses, valid
intervals, and topology versions is the remaining step before a real
cross-model disagreement study can be frozen. Until then this note describes the
method and the honesty constraint rather than reporting a specific measured
disagreement, and the status is recorded as pending in the specification.

## Interpretation

A measured disagreement between models, like a GNSS residual, is a prompt to ask
why: different data, different assumed fixed plates, different stage boundaries.
It is not an automatic discovery of a new tectonic law, and Lithora frames it
that way.
