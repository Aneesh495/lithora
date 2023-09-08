"""Synthetic known-truth deformation worlds (capability L23).

For honest evaluation we need worlds where the correct answer is known: a
rigid plate with a prescribed Euler vector, optional deforming zones, station
noise, missing stations, and out-of-domain regions. These let us verify that
the Euler fit recovers the truth within its stated uncertainty (gate G05) and
that the deformation baselines behave correctly where rigidity breaks down.

Everything here is explicitly synthetic and labelled as such. It must never be
presented as real observation.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .sphere import EARTH_RADIUS_M, cartesian_velocity_to_enu, euler_velocity, latlon_to_unit


@dataclass
class SyntheticWorld:
    """A generated station network with known truth.

    Attributes
    ----------
    lat_deg, lon_deg:
        Station coordinates, shape ``(n,)``.
    vel_en_mm_yr:
        Observed horizontal velocities (east, north) in mm/yr, shape
        ``(n, 2)``, including noise and any deformation signal.
    truth_vel_en_mm_yr:
        Noise-free rigid-plus-deformation truth, same shape.
    cov_en_mm_yr:
        Per-station 2x2 velocity covariance used to draw the noise.
    true_omega:
        The rigid Euler vector in rad/Myr, shape ``(3,)``.
    in_deforming_zone:
        Boolean mask marking stations inside a deforming zone.
    """

    lat_deg: np.ndarray
    lon_deg: np.ndarray
    vel_en_mm_yr: np.ndarray
    truth_vel_en_mm_yr: np.ndarray
    cov_en_mm_yr: np.ndarray
    true_omega: np.ndarray
    in_deforming_zone: np.ndarray


def make_rigid_plate(
    n_stations: int,
    pole_lat_deg: float,
    pole_lon_deg: float,
    rate_deg_per_myr: float,
    region_center: tuple[float, float],
    region_half_width_deg: float,
    noise_mm_yr: float = 0.5,
    seed: int = 0,
    deform_fraction: float = 0.0,
    deform_amp_mm_yr: float = 3.0,
) -> SyntheticWorld:
    """Generate a rigid plate with optional deformation and noise.

    Stations are scattered uniformly in a lat/lon box around ``region_center``.
    A fraction ``deform_fraction`` of stations (those nearest one edge) carry
    an added smooth deformation signal, so the plate is not perfectly rigid and
    a residual model has something real to learn.
    """
    rng = np.random.default_rng(seed)
    clat, clon = region_center
    lat = clat + rng.uniform(-region_half_width_deg, region_half_width_deg, n_stations)
    lon = clon + rng.uniform(-region_half_width_deg, region_half_width_deg, n_stations)
    lat = np.clip(lat, -89.0, 89.0)

    # True Euler vector.
    axis = latlon_to_unit(np.array([pole_lat_deg]), np.array([pole_lon_deg]))[0]
    omega = axis * np.radians(rate_deg_per_myr)

    r = latlon_to_unit(lat, lon)
    v_cart_unit = euler_velocity(omega, r)
    v_cart_mm = v_cart_unit * EARTH_RADIUS_M * 1e-3
    truth_en = cartesian_velocity_to_enu(v_cart_mm, lat, lon)

    # Deformation signal on a subset: a smooth east-gradient near the +lon edge.
    in_zone = np.zeros(n_stations, dtype=bool)
    if deform_fraction > 0:
        thresh = np.quantile(lon, 1.0 - deform_fraction)
        in_zone = lon >= thresh
        grad = (lon - thresh) / max(region_half_width_deg, 1e-6)
        truth_en[in_zone, 0] += deform_amp_mm_yr * grad[in_zone]

    # Noise with the given per-component standard deviation.
    cov = np.tile(np.eye(2) * noise_mm_yr**2, (n_stations, 1, 1))
    noise = np.stack(
        [rng.normal(0.0, noise_mm_yr, n_stations), rng.normal(0.0, noise_mm_yr, n_stations)],
        axis=-1,
    )
    obs_en = truth_en + noise

    return SyntheticWorld(
        lat_deg=lat,
        lon_deg=lon,
        vel_en_mm_yr=obs_en,
        truth_vel_en_mm_yr=truth_en,
        cov_en_mm_yr=cov,
        true_omega=omega,
        in_deforming_zone=in_zone,
    )
