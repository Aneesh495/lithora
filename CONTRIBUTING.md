# Contributing to Lithora

Lithora is a technical passion project. Contributions that deepen the science
or harden the engineering are welcome; the bar is that every change keeps the
project honest about what it measures.

## Ground rules

- Correctness over cleverness. The kinematics core is held to tight numerical
  tolerances; a change there needs a test that pins the invariant.
- No silent fabrication. Ages outside a model's range, missing circuit links,
  and absent uncertainty must surface as explicit errors or modelled
  missingness, never as a plausible default.
- Keep the two clocks separate. Do not add code that bridges present-day
  geodesy and deep-time reconstruction as if one measured the other.
- Reference frames never mix silently. Any new data path must carry the frame.

## Development loop

```
make bootstrap     # set up the venv and install the package
make build         # cargo build the workspace
make test          # rust + python tests
make doctor        # report the environment
```

For the Rust core, run `cargo fmt` and `cargo clippy -- -D warnings` before
committing; CI enforces both. For Python, keep functions typed and tested.

## Tests

- Rust: unit tests per module, property campaigns under `crates/*/tests`.
- Python: `pytest python`. Torch-dependent tests skip cleanly without torch.
- New features need a test; bug fixes need a regression test. Do not weaken a
  tolerance to make a test pass.

## Commits

Commit focused, reviewable increments with a message that states the behaviour
and the check behind it. Push frequently. Do not accumulate a large change into
one commit.

## Writing

Public prose explains mechanisms, assumptions, and measured behaviour. No
decorative banners, no restating the code in comments. Comments explain
invariants, ownership, units, and non-obvious numerical choices.
