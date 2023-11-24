# Artifact format

The files an acceptance run produces, and what each one means. A bundle is a
directory under `evidence/` containing these files.

## ENVIRONMENT.json

The Python version, platform, NumPy version, and the git source commit the run
was executed from. The commit ties the evidence to exact source.

## DATASETS.json

For each input dataset: the path, the reference frame, the SHA256 of the bytes,
and the byte count. The hash pins the exact input; a different download would
have a different hash and would invalidate affected evidence.

## OBSERVATIONS.json

The per-unit raw observations and computed results. Decisive quantities include
the raw station coordinates, velocities, and variances used in the rigid fit,
so the verifier can recompute the Euler pole independently rather than trusting
the stored pole. Each unit records enough to be rechecked.

## ACCEPTANCE.json

The profile name (for example `cpu-diagnostic`), start and finish times, and a
status. Only `completed` is accepted by the verifier; a partial or failed run
is not silently treated as passing.

## MANIFEST.json

A map from each component filename to its SHA256. This is an integrity check,
not a semantic one: the verifier recomputes the science from OBSERVATIONS.json
and only uses the manifest to detect byte-level tampering. A negative control
re-seals the manifest after editing a result precisely to prove the verifier
does not rely on the manifest for correctness.

## Verifier contract

`verify.py` reads MANIFEST, ACCEPTANCE, DATASETS, and OBSERVATIONS; checks the
hashes; confirms the status; recomputes the data-coverage floor, the Euler pole
(independently), and the model-comparison relationship; and returns nonzero on
any disagreement. It never retrains, re-downloads, or trusts a stored pass
flag.

## Reproducing a bundle

```
make acceptance RUN_ID=<new-id> PROFILE=full   # writes evidence/<new-id>
make verify EVIDENCE=evidence/<new-id>
make negative-controls EVIDENCE=evidence/<new-id>
```

Bundles live under `evidence/` which is gitignored; only the source and the
provenance manifests are committed.
