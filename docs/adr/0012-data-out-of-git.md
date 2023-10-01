# 12. Cache raw data out of Git with provenance manifests

## Context

GNSS and earthquake datasets are large and may carry redistribution
constraints. They must be reproducible without bloating the repository or
committing restricted bytes.

## Decision

Download into a gitignored cache (`data/raw`) and commit only small JSON
provenance manifests (source, URL, citation, frame, SHA256, byte count,
timestamp) and the acquisition code.

## Alternatives

- Commit the raw data: bloats the repo and risks redistributing restricted
  files.
- Commit nothing about the data: loses reproducibility and provenance.

## Consequences

A fresh checkout reproduces the data with one acquisition command, and the
manifests let anyone audit exactly what was fetched. A small, committed sample
under `web/public/data` lets the atlas run from a fresh checkout without any
download. The SHA256 in each manifest ties final evidence to specific input
bytes.
