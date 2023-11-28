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

.PHONY: all bootstrap doctor build test data demo bench stress docs acceptance verify negative-controls release \
        acquire-gnss acquire-quakes export-web reconstruct fit-plates train spatial-evaluate atlas paper clean

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

data: acquire-gnss acquire-quakes export-web
	@echo "data acquired and exported for the atlas"

acquire-gnss: $(VENV)
	$(PY) -m lithora.cli acquire-gnss --frame IGS14

acquire-quakes: $(VENV)
	$(PY) -m lithora.export_quakes --region cal --start 2014-01-01 --end 2024-01-01 --min-mag 4.0 --out web/public/data/quakes_cal.json
	$(PY) -m lithora.export_quakes --region na --start 2014-01-01 --end 2024-01-01 --min-mag 4.0 --out web/public/data/quakes_na.json

export-web: $(VENV)
	$(PY) -m lithora.export_web --frame IGS14 --region cal --out web/public/data/cal.json
	$(PY) -m lithora.export_web --frame IGS14 --region na --out web/public/data/na.json

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

paper: $(VENV)
	@echo "Regenerating reproducible views behind the research notes..."
	$(PY) notebooks/01_regional_comparison.py
	$(PY) notebooks/02_strain_scale_sweep.py
	@echo "Research report: docs/research/ (12 notes) and docs/FINDINGS.md"

## ---- heavier phases ----

bench:
	cargo bench -p lithora-geo --bench reconstruct_throughput

stress:
	@echo "Stress campaign not yet wired; see docs/EXPERIMENT_PLAN.md"

docs:
	@echo "Docs live under docs/. Diagrams under docs/diagrams (make diagrams)."

acceptance: $(VENV)
	@test -n "$(RUN_ID)" || (echo "set RUN_ID=<new-id>"; exit 1)
	$(PY) -m lithora.acceptance --evidence evidence/$(RUN_ID) --frame IGS14

verify: $(VENV)
	@test -n "$(EVIDENCE)" || (echo "set EVIDENCE=<path>"; exit 1)
	$(PY) -m lithora.verify --evidence $(EVIDENCE)

negative-controls: $(VENV)
	@test -n "$(EVIDENCE)" || (echo "set EVIDENCE=<path>"; exit 1)
	$(PY) -m lithora.negative_controls --evidence $(EVIDENCE)

release: build test
	@echo "Release packaging: fresh-checkout build + test + demo."

clean:
	cargo clean
	rm -rf python/build python/*.egg-info
