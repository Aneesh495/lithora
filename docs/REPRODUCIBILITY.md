# Reproducibility

Every figure and number in Lithora's research notes traces to a command and an
exact input. This document gives the full path.

## Environment

- Rust 1.80+ (developed on 1.88), Python 3.10+ (developed on 3.14).
- `make bootstrap` creates the Python venv and installs the package.
- `make doctor` reports the exact toolchain, packages, and data cache so a
  reader can confirm their environment matches.

## Data

Real data is acquired, not committed. `make acquire-gnss` downloads the NGL
MIDAS IGS14 velocities and writes a provenance manifest with the SHA256 of the
exact bytes. The upstream file updates weekly, so pin a snapshot by its hash
for a reproducible campaign. A small derived sample is committed under
`web/public/data` so the atlas runs from a fresh checkout.

## Deterministic components

- The Rust geometry property campaign uses a seeded SplitMix64 generator, so
  every random case is replayable from its seed.
- The synthetic worlds and spatial folds use seeded NumPy generators.
- Learned runs set the torch and NumPy seeds; the registry records the seed,
  hyperparameters, and exact held-out station ids per fold.

## Reproducing the headline results

```
make bootstrap
make acquire-gnss
python -m lithora.cli fit-plates --frame IGS14 --region na          # note 03
python -m lithora.cli spatial-evaluate --frame IGS14 --region cal   # note 11
python -m lithora.cli train --frame IGS14 --region cal --seed 0     # note 11
python -m lithora.cli strain --lat 36 --lon -120.5                  # note 11
python notebooks/01_regional_comparison.py
python notebooks/02_strain_scale_sweep.py
```

Rust correctness gates:

```
cargo test --workspace
cargo test -p lithora-geo --test g01_geometry --release
cargo test -p lithora-geo --test g02_reconstruction --release
cargo test -p lithora-recon --test g12_cache_stress --release
```

## Evidence and verification

```
make acceptance RUN_ID=<id> PROFILE=full
make verify EVIDENCE=evidence/<id>
make negative-controls EVIDENCE=evidence/<id>
```

The verifier recomputes decisive quantities independently from the raw records,
so a bundle that passes has been checked, not merely declared.

## Caveats on exact reproduction

- Learned-model numbers vary with the seed; the research notes report the
  spread across seeds rather than a single run.
- A new MIDAS download will differ from the pinned snapshot; cross-region
  conclusions are stable, but exact RMSE values will shift slightly.
- Absolute throughput from `make bench` is machine dependent; report it with
  the host.
