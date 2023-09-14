"""Tests for tangent frames and parallel transport."""

import numpy as np

from lithora.sphere import latlon_to_unit
from lithora.transport import (
    exp_map,
    log_map,
    parallel_transport,
    tangent_frame,
)


def test_tangent_frame_orthonormal_and_tangent():
    pos = latlon_to_unit(np.array([35.0]), np.array([120.0]))[0]
    e, n = tangent_frame(pos)
    assert abs(np.dot(e, n)) < 1e-12
    assert abs(np.dot(e, pos)) < 1e-12
    assert abs(np.dot(n, pos)) < 1e-12
    assert abs(np.linalg.norm(e) - 1) < 1e-12


def test_log_exp_round_trip():
    a = latlon_to_unit(np.array([10.0]), np.array([20.0]))[0]
    b = latlon_to_unit(np.array([15.0]), np.array([28.0]))[0]
    lv = log_map(a, b)
    back = exp_map(a, lv)
    assert np.allclose(back, b, atol=1e-10)


def test_log_map_length_is_great_circle_angle():
    a = latlon_to_unit(np.array([0.0]), np.array([0.0]))[0]
    b = latlon_to_unit(np.array([0.0]), np.array([30.0]))[0]
    lv = log_map(a, b)
    assert abs(np.linalg.norm(lv) - np.radians(30.0)) < 1e-10


def test_parallel_transport_preserves_length():
    a = latlon_to_unit(np.array([5.0]), np.array([10.0]))[0]
    b = latlon_to_unit(np.array([25.0]), np.array([40.0]))[0]
    e, n = tangent_frame(a)
    v = 2.3 * e - 1.1 * n
    tv = parallel_transport(a, b, v)
    assert abs(np.linalg.norm(tv) - np.linalg.norm(v)) < 1e-10
    # Transported vector must be tangent at b.
    assert abs(np.dot(tv, b)) < 1e-10


def test_transport_is_identity_for_same_point():
    a = latlon_to_unit(np.array([1.0]), np.array([2.0]))[0]
    e, _ = tangent_frame(a)
    assert np.allclose(parallel_transport(a, a, e), e)


def test_transport_round_trip_returns_original():
    a = latlon_to_unit(np.array([0.0]), np.array([0.0]))[0]
    b = latlon_to_unit(np.array([10.0]), np.array([0.0]))[0]
    e, n = tangent_frame(a)
    v = e + 0.5 * n
    there = parallel_transport(a, b, v)
    back = parallel_transport(b, a, there)
    assert np.allclose(back, v, atol=1e-10)
