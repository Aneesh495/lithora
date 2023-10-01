# Architecture decision records

Each ADR records a real decision, the alternatives weighed, and the
consequences accepted. They are short on purpose; the reasoning, not ceremony,
is the point.

1. Rust for the kinematics core
2. Unit quaternions for finite rotations
3. Slerp for rotation interpolation
4. Explicit error taxonomy: bad input versus unsupported request
5. Python for inference, with torch optional
6. Reference frame as a typed, non-mergeable attribute
7. Linear weighted least squares for the Euler pole
8. Tangent-frame transport for the learned model
9. Spatially buffered folds for evaluation
10. Independent verifier separate from the summarizer
11. CesiumJS for the atlas
12. Cache raw data out of Git with provenance manifests
13. SplitMix64 for reproducible property tests
