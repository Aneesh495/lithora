# Plate circuits

Plates move relative to their neighbours, which move relative to theirs, up to
an anchor. Reconstructing a plate relative to the anchor means composing finite
rotations along this chain, and the chain is a time-dependent directed graph
because parent relationships change with age.

## Composition order is the whole game

If a plate's motion to its parent is `q_1` and the parent's motion to the
anchor is `q_2`, the total rotation applies `q_1` first and then `q_2`, which is
the quaternion product `q_2 q_1`. Reversing the order is the classic circuit
bug, and because quaternion multiplication does not commute, the reversed order
lands the plate somewhere else. The code encodes the temporal order in the
method name `then`, so call sites read in the order events happen while the
reversed multiplication is hidden inside. A test composes three noncommuting
rotations and checks the result against the manual product.

## Re-anchoring must be consistent

Changing the anchor must rotate the entire reconstruction by one common
rotation: `q(M -> A') = q(M -> A) then q(A -> A')`. A test reconstructs a plate
relative to two anchors and confirms the relationship holds exactly, which
guarantees the atlas can switch anchors without silently distorting geometry.

## Model choices versus parsing errors

A rotation model has real discontinuities where a plate changes parent or where
a stage pole flips. These are geological choices in the published model, and
they must be preserved, not smoothed. A missing interval, by contrast, means
the model simply does not cover that time, and Lithora returns an explicit
`AgeOutOfRange` or `NoBracket` error rather than extrapolating. A cycle in the
declared parent relationships is a data or parsing error, detected during
traversal and returned as `CircuitCycle`. Keeping these three cases distinct is
what separates a faithful reconstruction from a plausible-looking fabrication.

## Toy circuits

The tests build exact two- and three-plate circuits with noncommuting
rotations, same-axis rotations that must add, and age ranges that must reject
out-of-range queries. These are the known-truth cases that anchor the engine
before it ever sees a real published model.
