# Walkthrough: error and recovery paths

This traces what happens when things go wrong, which is where a system's
honesty is tested. Four failure paths are covered.

## 1. Reconstructing past a model's valid interval

```
cargo run -p lithora-cli -- reconstruct --rot model.rot --plate 801 --lat 12 --lon 45 --age 500
```

If 500 Ma is beyond the model's samples, `RotationSequence::rotation_at`
(`sequence.rs`) returns `GeoError::AgeOutOfRange { age, min, max }`. The circuit
traversal propagates it, `reconstruct_point` returns the error, and the CLI
prints it and exits nonzero. The system never extrapolates through an absent
interval to produce a plausible but unsupported number. The demo output ends
with a note that ages beyond the model range error by design.

## 2. A corrupt rotation file

A line with a bad latitude or too few fields causes `parse_rot`
(`rot_format.rs`) to return `RotParseError::BadLatitude` or `TooFewFields` with
the offending line number. The model never loads with a silently defaulted
field. The unit tests cover each malformed case.

## 3. A missing GNSS cache

```
python -m lithora.cli fit-plates --frame IGS14 --region na   # with no cache
```

`cli._load_field` checks for the cached file and, if absent, prints
`run acquire-gnss first` to stderr and exits with status 2, rather than failing
inside the parser with an opaque error.

## 4. Interrupted training and verifier rejection

Training saves checkpoints atomically: `train.save_checkpoint` writes to a temp
file in the same directory and `os.replace`s it into place, so an interruption
during the write leaves the previous good checkpoint intact (never a
half-written file). On the evidence side, `verify.verify` recomputes the Euler
pole independently and raises `VerificationError` on any semantic disagreement;
the negative controls in `negative_controls.py` prove it rejects a reversed
pole, a mm/metre scale error, a flipped comparison claim, a data-floor lie, a
manifest-hash mismatch, and a missing artifact, each with the correct reason.

## The principle

Each of these is an explicit, typed failure with enough context to act on, not
a silent wrong answer. The error taxonomy (ADR 4) exists precisely to keep "fix
your input" distinct from "this model cannot answer that".
