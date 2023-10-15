"""Strain-rate estimation from a velocity field (capability L21).

The horizontal strain-rate tensor measures how a velocity field stretches and
shears the crust. It is the symmetric part of the surface velocity gradient,
and its principal values and directions describe extension, compression, and
shear at a point. This is only meaningful at a declared smoothing scale: the
gradient of a noisy, irregularly sampled field is ill posed, so we estimate it
by fitting a local linear velocity model (the same distance-weighted fit the
baselines use) and reading off its spatial derivatives.

Everything here is explicit about the smoothing scale, the units, and the fact
that inferred strain changes with that scale. We report the scale alongside the
result and provide a function to sweep it, because a single strain number
without its smoothing bandwidth is not interpretable.

Units: velocities are mm/yr, distances are converted to metres on the sphere,
so strain rate has units of (mm/yr)/m = 1/yr, which we report in nanostrain per
year (1e-9 / yr), the conventional geodetic unit.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .baselines import great_circle_angles
from .sphere import EARTH_RADIUS_M


@dataclass
class StrainResult:
    """Strain rate at one query point.

    exx, eyy, exy:
        Components of the symmetric horizontal strain-rate tensor in
        nanostrain per year (east-east, north-north, east-north).
    dilatation:
        Trace exx + eyy, the areal strain rate (positive = extension).
    max_shear:
        Maximum shear strain rate.
    principal_angle_deg:
        Azimuth of the most-extensional principal axis, degrees east of north.
    smoothing_scale_deg:
        The bandwidth used, which the result depends on.
    n_effective:
        Effective number of stations contributing (sum of weights).
    """

    exx: float
    eyy: float
    exy: float
    dilatation: float
    max_shear: float
    principal_angle_deg: float
    smoothing_scale_deg: float
    n_effective: float


def strain_rate_at(
    lat_q: float,
    lon_q: float,
    lat: np.ndarray,
    lon: np.ndarray,
    vel_en: np.ndarray,
    smoothing_scale_deg: float = 1.0,
) -> StrainResult:
    """Estimate the strain-rate tensor at one point from nearby velocities.

    We fit, separately for the east and north velocity components, a local
    linear model ``v = a + b*x + c*y`` in a local tangent frame (x east, y
    north, in metres), weighting stations by a Gaussian of their great-circle
    distance with the given bandwidth. The velocity gradient is then
    ``[[b_e, c_e], [b_n, c_n]]`` and the strain rate is its symmetric part.
    """
    lat = np.asarray(lat, float).reshape(-1)
    lon = np.asarray(lon, float).reshape(-1)
    vel = np.asarray(vel_en, float).reshape(-1, 2)

    bw = np.radians(smoothing_scale_deg)
    d = great_circle_angles(np.array([lat_q]), np.array([lon_q]), lat, lon)[0]
    w = np.exp(-0.5 * (d / bw) ** 2)
    n_eff = float(w.sum())
    if n_eff < 3:
        # Not enough local support to estimate a gradient.
        return StrainResult(0, 0, 0, 0, 0, 0, smoothing_scale_deg, n_eff)

    # Local tangent offsets in metres (small-angle: arc length = angle * R).
    dx = np.radians(lon - lon_q) * np.cos(np.radians(lat_q)) * EARTH_RADIUS_M
    dy = np.radians(lat - lat_q) * EARTH_RADIUS_M
    design = np.stack([np.ones_like(dx), dx, dy], axis=1)

    grad = np.zeros((2, 2))  # rows: [de/dx de/dy; dn/dx dn/dy]
    for comp in range(2):
        wd = w[:, None] * design
        ata = design.T @ wd
        atb = design.T @ (w * vel[:, comp])
        coef = np.linalg.solve(ata + 1e-6 * np.eye(3), atb)
        grad[comp, 0] = coef[1]  # d v_comp / dx
        grad[comp, 1] = coef[2]  # d v_comp / dy

    # Strain rate is the symmetric part of the gradient. Velocities are mm/yr,
    # distances metres, so components are (mm/yr)/m = 1e-3 /yr; convert to
    # nanostrain/yr by multiplying by 1e-3 / 1e-9 = 1e6.
    to_nanostrain = 1e6
    exx = grad[0, 0] * to_nanostrain
    eyy = grad[1, 1] * to_nanostrain
    exy = 0.5 * (grad[0, 1] + grad[1, 0]) * to_nanostrain

    dilatation = exx + eyy
    # Principal values of the 2x2 symmetric tensor.
    mean = 0.5 * (exx + eyy)
    radius = np.hypot(0.5 * (exx - eyy), exy)
    max_shear = radius
    # Azimuth of the most-extensional principal axis (largest eigenvalue).
    angle = 0.5 * np.degrees(np.arctan2(2 * exy, exx - eyy))

    return StrainResult(
        exx=float(exx), eyy=float(eyy), exy=float(exy),
        dilatation=float(dilatation), max_shear=float(max_shear),
        principal_angle_deg=float(angle), smoothing_scale_deg=smoothing_scale_deg,
        n_effective=n_eff,
    )


def strain_scale_sweep(
    lat_q: float,
    lon_q: float,
    lat: np.ndarray,
    lon: np.ndarray,
    vel_en: np.ndarray,
    scales_deg: list[float],
) -> list[StrainResult]:
    """Estimate strain at a point across several smoothing scales.

    The point of this is honesty: inferred strain depends on the smoothing
    scale, and showing the sweep makes that dependence explicit rather than
    reporting one scale as if it were the truth.
    """
    return [strain_rate_at(lat_q, lon_q, lat, lon, vel_en, s) for s in scales_deg]
