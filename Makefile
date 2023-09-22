# Lithora build and workflow entry points.
#
# The Rust core builds and tests with cargo; the Python layer uses a virtual
# environment under python/.venv. Targets that need network or heavy compute
# are separated from the fast developer loop so a plain `make test` stays quick.

PYTHON ?= python3
VENV := python/.venv
PY := $(VENV)/bin/python
PIP := $(VENV)/bin/pip
PYTEST := $(VENV)/bin/pytest

.PHONY: all bootstrap doctor build test data demo bench stress docs acceptance verify release \
        acquire-gnss reconstruct fit-plates train spatial-evaluate atlas paper clean

all: build test

## ---- setup ----

bootstrap: $(VENV)
	@echo "Rust toolchain:" && cargo --version
	$(PIP) install -q -e "python/.[dev]"
	@echo "bootstrap complete"

$(VENV):
	$(PYTHON) -m venv $(VENV)
	$(PIP) install -q --upgrade pip

doctor:
	@echo "== toolchains =="
	@cargo --version || echo "cargo MISSING"
	@rustc --version || echo "rustc MISSING"
	@$(PY) --version || echo "python venv MISSING (run make bootstrap)"
	@echo "== python packages =="
	@$(PY) -c "import numpy,scipy; print('numpy',numpy.__version__,'scipy',scipy.__version__)" 2>/dev/null || echo "numpy/scipy MISSING"
	@$(PY) -c "import torch; print('torch',torch.__version__,'mps',torch.backends.mps.is_available())" 2>/dev/null || echo "torch not installed (learning gated off)"
	@echo "== data cache =="
	@ls -1 data/raw/gnss 2>/dev/null || echo "no GNSS cache (run make acquire-gnss)"

## ---- build and test ----

build:
	cargo build --workspace

test: test-rust test-python

test-rust:
	cargo test --workspace

test-python: $(VENV)
	$(PYTEST) python -q

## ---- the required domain commands ----

demo:
	cargo run -p lithora-cli -- demo

acquire-gnss: $(VENV)
	$(PY) -m lithora.cli acquire-gnss --frame IGS14

reconstruct:
	cargo run -p lithora-cli -- reconstruct --plate 801 --lat 12 --lon 45 --age 50

fit-plates: $(VENV)
	$(PY) -m lithora.cli fit-plates --frame IGS14

train: $(VENV)
	$(PY) -m lithora.cli train --frame IGS14

spatial-evaluate: $(VENV)
	$(PY) -m lithora.cli spatial-evaluate --frame IGS14

atlas:
	@echo "Interactive globe under web/ (see web/README.md). Run: cd web && npm install && npm run dev"

paper:
	@echo "Research report under docs/research/. See docs/research/README.md"

## ---- heavier phases ----

bench:
	cargo test --workspace --release -- --nocapture bench_ 2>/dev/null || echo "add benches as needed"

stress:
	@echo "Stress campaign not yet wired; see docs/EXPERIMENT_PLAN.md"

docs:
	@echo "Docs live under docs/. Diagrams under docs/diagrams (make diagrams)."

acceptance:
	@echo "Full acceptance campaign (see docs/EXPERIMENT_PLAN.md). RUN_ID=$(RUN_ID) PROFILE=$(PROFILE)"

verify:
	$(PY) -m lithora.verify --evidence $(EVIDENCE)

release: build test
	@echo "Release packaging: fresh-checkout build + test + demo."

clean:
	cargo clean
	rm -rf python/build python/*.egg-info
