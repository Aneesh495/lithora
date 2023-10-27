# Walkthrough: reconstructing a point to a geological age

This traces the complete path from a CLI call to a reconstructed position,
naming every function it passes through.

## The call

```
cargo run -p lithora-cli -- reconstruct --rot model.rot --plate 801 --lat 12 --lon 45 --age 50
```

## Step by step

1. `crates/lithora-cli/src/main.rs` parses the arguments with clap and calls
   `load_model`, which reads the rotation file and builds a `Model`.
2. `Model::from_rot_text` (`crates/lithora-recon/src/reconstruct.rs`) calls
   `parse_rot` (`rot_format.rs`), which turns each line into a `RotRecord`.
   A malformed line raises `RotParseError` with the line number here rather
   than defaulting a field.
3. `group_sequences` groups records by (moving, fixed) plate into
   `RotationSequence` values, each sorted by age, and `PlateCircuit::add_link`
   stores them.
4. `Model::reconstruct_point` calls `PlateCircuit::total_rotation(plate,
   anchor, age)` (`circuit.rs`). This walks the parent chain from the moving
   plate to the anchor.
5. For each link, `RotationSequence::rotation_at(age)` (`sequence.rs`) finds the
   bracketing age samples and `slerp`s between their quaternions. An age outside
   the samples returns `GeoError::AgeOutOfRange` and the whole reconstruction
   fails cleanly.
6. The per-link rotations compose with `Rotation::then` (`rotation.rs`), which
   performs the reversed quaternion product so the call reads in temporal order.
7. Back in `reconstruct_point`, the total rotation is applied to the point's
   unit vector with `Rotation::apply`, and `LatLon::from_vec` converts back to
   geographic coordinates.
8. `main.rs` prints the result as JSON.

## What makes it correct

The age interpolation is on the rotation (slerp), not the point, so the
reconstructed position stays on the sphere. The composition order is temporal.
An unsupported age is an explicit error, never an extrapolation. See the
rendered sequence diagram at `docs/diagrams/reconstruct_path.svg`.
