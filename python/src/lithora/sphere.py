"""Spherical geometry helpers for the Python inference layer.

These mirror the conventions of the Rust ``lithora-geo`` core so that results
are comparable: geocentric spherical coordinates, unit-vector positions, and
angular velocities as Euler vectors in radians per million years. The Python
side uses these for Euler-pole fitting and the deformation baselines, where
NumPy's vectorisation matters; the authoritative reconstruction engine remains
the Rust core.

Conventions (identical to the Rust side):

* latitude positive north in degrees, longitude positive east in degrees;
* unit vector ``x = cos(lat) cos(lon)``, ``y = cos(lat) sin(lon)``,
  ``z = sin(lat)``;
* an Euler vector ``omega`` gives surface velocity ``v = omega x r``.
"""

from __future__ import annotations

import numpy as np

EARTH_RADIUS_M = 6_371_008.8


def latlon_to_unit(lat_deg: np.ndarray, lon_deg: np.ndarray) -> np.ndarray:
    """Map geographic coordinates to unit vectors.

    Accepts scalars or arrays. Returns an array of shape ``(..., 3)``.
    """
    lat = np.radians(np.asarray(lat_deg, dtype=float))
    lon = np.radians(np.asarray(lon_deg, dtype=float))
    clat = np.cos(lat)
    return np.stack([clat * np.cos(lon), clat * np.sin(lon), np.sin(lat)], axis=-1)


def unit_to_latlon(vec: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Recover (lat_deg, lon_deg) from unit (or non-unit) vectors."""
    vec = np.asarray(vec, dtype=float)
    x, y, z = vec[..., 0], vec[..., 1], vec[..., 2]
    r_xy = np.hypot(x, y)
    lat = np.degrees(np.arctan2(z, r_xy))
    lon = np.degrees(np.arctan2(y, x))
    return lat, lon


def local_enu_basis(lat_deg: np.ndarray, lon_deg: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return the local east, north, up unit vectors at each location.

    The tangent-plane east/north basis is what GNSS velocities are reported
    in, so converting a Cartesian velocity into east/north components uses
    these. ``up`` equals the position unit vector on a sphere.
    """
    lat = np.radians(np.asarray(lat_deg, dtype=float))
    lon = np.radians(np.asarray(lon_deg, dtype=float))
    east = np.stack([-np.sin(lon), np.cos(lon), np.zeros_like(lon)], axis=-1)
    north = np.stack(
        [-np.sin(lat) * np.cos(lon), -np.sin(lat) * np.sin(lon), np.cos(lat)],
        axis=-1,
    )
    up = latlon_to_unit(np.degrees(lat), np.degrees(lon))
    return east, north, up


def euler_velocity(omega: np.ndarray, positions_unit: np.ndarray) -> np.ndarray:
    """Surface velocity ``v = omega x r`` for one Euler vector and many points.

    ``omega`` has shape ``(3,)`` in rad/Myr; ``positions_unit`` has shape
    ``(n, 3)``. Returns ``(n, 3)`` Cartesian velocity with the same length
    scale as ``omega`` times the unit radius (multiply by Earth radius and the
    mm/yr factor to get geodetic units).
    """
    omega = np.asarray(omega, dtype=float).reshape(3)
    return np.cross(np.broadcast_to(omega, positions_unit.shape), positions_unit)


def cartesian_velocity_to_enu(
    vel_cart: np.ndarray, lat_deg: np.ndarray, lon_deg: np.ndarray
) -> np.ndarray:
    """Project Cartesian surface velocities onto local east/north.

    Returns an array of shape ``(n, 2)`` with columns (east, north). The
    radial component is dropped because plate motion is tangential; a small
    nonzero radial part from numerical error is discarded here deliberately.
    """
    east, north, _ = local_enu_basis(lat_deg, lon_deg)
    ve = np.sum(vel_cart * east, axis=-1)
    vn = np.sum(vel_cart * north, axis=-1)
    return np.stack([ve, vn], axis=-1)


def rad_per_myr_to_mm_per_yr(vel_cart_unit: np.ndarray, radius_m: float = EARTH_RADIUS_M) -> np.ndarray:
    """Convert unit-radius rad/Myr velocity magnitudes to mm/yr.

    A velocity expressed at unit radius in rad/Myr becomes a length rate of
    ``|v| * radius`` metres per Myr, and 1 m/Myr = 1e-3 mm/yr.
    """
    return vel_cart_unit * radius_m * 1e-3
