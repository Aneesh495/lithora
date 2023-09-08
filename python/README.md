# lithora (Python inference layer)

Euler-pole fitting, deterministic deformation baselines, synthetic known-truth
worlds, and the spherical graph residual model for Lithora. The authoritative
reconstruction engine is the Rust `lithora-geo` crate; this package consumes
its conventions and adds the statistical and learned inference.

## Install

```
python -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"
```

The learned graph model needs PyTorch:

```
pip install -e ".[learn]"
```

## Test

```
pytest
```
