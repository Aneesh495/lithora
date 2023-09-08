"""Tests for the spherical geometry helpers."""

import numpy as np

from lithora.sphere import (
    cartesian_velocity_to_enu,
    euler_velocity,
    latlon_to_unit,
    local_enu_basis,
    unit_to_latlon,
)


def test_latlon_unit_round_trip():
    lat = np.array([0.0, 37.5, -67.8, 89.0])
    lon = np.array([0.0, -122.3, 100.0, 45.0])
    v = latlon_to_unit(lat, lon)
    assert np.allclose(np.linalg.norm(v, axis=-1), 1.0)
    rlat, rlon = unit_to_latlon(v)
    assert np.allclose(rlat, lat, atol=1e-9)
    # longitude at the near-pole point can wrap; check the others.
    assert np.allclose(rlon[:3], lon[:3], atol=1e-9)


def test_enu_basis_orthonormal():
    lat = np.array([12.0, -45.0])
    lon = np.array([34.0, 150.0])
    east, north, up = local_enu_basis(lat, lon)
    for i in range(2):
        assert abs(np.dot(east[i], north[i])) < 1e-12
        assert abs(np.dot(east[i], up[i])) < 1e-12
        assert abs(np.dot(north[i], up[i])) < 1e-12
        assert abs(np.linalg.norm(east[i]) - 1.0) < 1e-12


def test_euler_velocity_tangent_and_pole_zero():
    omega = np.array([0.0, 0.0, 0.5])  # about +z
    pts = latlon_to_unit(np.array([0.0, 90.0]), np.array([0.0, 0.0]))
    v = euler_velocity(omega, pts)
    # At the equator, velocity is tangent (perpendicular to position).
    assert abs(np.dot(v[0], pts[0])) < 1e-15
    # At the north pole (rotation axis), velocity vanishes.
    assert np.linalg.norm(v[1]) < 1e-15


def test_enu_projection_direction():
    # A rotation about +z moves an equatorial point eastward.
    omega = np.array([0.0, 0.0, 0.1])
    lat = np.array([0.0])
    lon = np.array([0.0])
    pts = latlon_to_unit(lat, lon)
    v = euler_velocity(omega, pts)
    en = cartesian_velocity_to_enu(v, lat, lon)
    assert en[0, 0] > 0  # eastward
    assert abs(en[0, 1]) < 1e-12  # no north component at the equator
