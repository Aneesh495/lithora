"""Lithora Python inference layer.

This package provides the parts of Lithora that benefit from NumPy, SciPy, and
(optionally) PyTorch: Euler-pole fitting, deterministic deformation baselines,
synthetic known-truth worlds, and the spherical graph residual model. The
authoritative reconstruction and kinematics engine lives in the Rust
``lithora-geo`` crate; this layer consumes its conventions.
"""

from __future__ import annotations

from .euler_fit import EulerFit, fit_euler_pole, predict_velocities
from .sphere import (
    EARTH_RADIUS_M,
    euler_velocity,
    latlon_to_unit,
    local_enu_basis,
    unit_to_latlon,
)

__all__ = [
    "EARTH_RADIUS_M",
    "EulerFit",
    "fit_euler_pole",
    "predict_velocities",
    "euler_velocity",
    "latlon_to_unit",
    "local_enu_basis",
    "unit_to_latlon",
]

__version__ = "0.1.0"
