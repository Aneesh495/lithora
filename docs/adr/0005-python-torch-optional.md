# 5. Python for inference, with torch optional

## Context

The statistical and learned inference is natural in Python, but PyTorch is a
heavy dependency and may be unavailable or hard to install on some
environments (including very new Python versions).

## Decision

Build the Python layer on NumPy/SciPy and make PyTorch an optional `learn`
extra. The graph model imports torch lazily and raises a clear error if it is
missing; torch-dependent tests skip cleanly.

## Alternatives

- Require torch always: simpler code, but the whole package becomes
  uninstallable where torch is unavailable, blocking the fitting and baselines
  that need no torch.
- Reimplement autodiff by hand: wasteful and error prone.

## Consequences

The Euler fit, baselines, GP, data layer, and evaluation run with no torch. The
learned model is available when the extra is installed. The test suite reports
how many tests skipped so the torch coverage is visible rather than silent.
