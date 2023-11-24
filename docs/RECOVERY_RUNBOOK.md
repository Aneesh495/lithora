# Recovery runbook

What to do when something fails. Each entry names the symptom, the cause, and
the fix.

## Acquisition fails with a TLS certificate error

Symptom: `acquire-gnss` raises `CERTIFICATE_VERIFY_FAILED`.

Cause: a proxy or gateway presents a root certificate trusted by the OS but not
by Python's bundled store.

Fix: Lithora already prefers the OS trust store via `truststore`
(`data/http.py`). Ensure `truststore` is installed (it is a dependency). If a
corporate CA is still not trusted by the OS, add it to the system keychain.

## Reconstruction returns AgeOutOfRange

Symptom: a reconstruct or motion-path call errors with an age outside the
supported range.

Cause: the requested age is beyond the rotation model's sampled interval. This
is intended behaviour, not a bug.

Fix: query an age within the model's range, or use a model whose valid interval
covers the age. Do not expect extrapolation.

## fit-plates says the GNSS cache is missing

Symptom: `error: no cached GNSS file ... Run acquire-gnss first` (exit 2).

Cause: the MIDAS file has not been downloaded, or the command was run from a
directory where `data/raw/gnss` does not resolve.

Fix: run from the repository root and run `make acquire-gnss` (or
`python -m lithora.cli acquire-gnss`) first.

## Training errors that torch is missing

Symptom: `train` prints that PyTorch is not installed (exit 2).

Cause: the optional `learn` extra is not installed.

Fix: `pip install -e "python/.[learn]"`. The rest of the package (fitting,
baselines, evaluation) works without torch.

## An interrupted training run

Symptom: training was killed partway.

Cause: external interruption.

Fix: checkpoints are written atomically (temp file then rename), so the last
good checkpoint is intact. Reload it with `train.load_checkpoint` and resume or
re-evaluate. A half-written file cannot occur because the rename is atomic.

## The verifier rejects an evidence bundle

Symptom: `verify` prints `REJECTED` with a reason.

Cause: a decisive quantity in the bundle disagrees with an independent
recomputation, a manifest hash is wrong, or a required file is missing.

Fix: do not edit the bundle to pass. Regenerate it with `acceptance` from the
exact source commit; the rejection means the stored result does not match the
raw records, which is the verifier working as intended.

## CI fmt or clippy failure

Symptom: CI fails on the Rust job.

Fix: run `cargo fmt --all` and `cargo clippy --workspace --all-targets -- -D
warnings` locally, fix the reported issues, re-stage, and commit a new fix.
