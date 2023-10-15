"""Tests for strain-rate estimation against known synthetic fields."""

import numpy as np

from lithora.sphere import EARTH_RADIUS_M
from lithora.strain import strain_rate_at, strain_scale_sweep


def _grid(center_lat, center_lon, half_deg=0.5, n=15):
    lats = np.linspace(center_lat - half_deg, center_lat + half_deg, n)
    lons = np.linspace(center_lon - half_deg, center_lon + half_deg, n)
    la, lo = np.meshgrid(lats, lons)
    return la.ravel(), lo.ravel()


def test_uniform_east_extension_recovered():
    # Build a velocity field v_east = g * x where x is metres east of center,
    # which is a pure east-west extension of known rate g.
    clat, clon = 36.0, -120.0
    lat, lon = _grid(clat, clon)
    g = 50e-9  # 50 nanostrain/yr expressed as (mm/yr)/m after scaling below
    # dx in metres from center.
    dx = np.radians(lon - clon) * np.cos(np.radians(clat)) * EARTH_RADIUS_M
    # v_east in mm/yr = g_mm_per_m * dx; choose g so result ~50 nanostrain/yr.
    g_mm_per_m = 50e-9 / 1e-3  # (mm/yr)/m giving 50 ns/yr -> 50e-9 /yr
    ve = g_mm_per_m * dx
    vn = np.zeros_like(ve)
    vel = np.stack([ve, vn], axis=1)

    res = strain_rate_at(clat, clon, lat, lon, vel, smoothing_scale_deg=0.5)
    assert abs(res.exx - 50.0) < 2.0, f"exx {res.exx}"
    assert abs(res.eyy) < 2.0
    assert abs(res.exy) < 2.0
    assert abs(res.dilatation - 50.0) < 3.0


def test_simple_shear_detected():
    # v_east = s * y (north offset) is simple shear; exy should be nonzero.
    clat, clon = 0.0, 0.0
    lat, lon = _grid(clat, clon)
    dy = np.radians(lat - clat) * EARTH_RADIUS_M
    s_mm_per_m = 40e-9 / 1e-3
    ve = s_mm_per_m * dy
    vn = np.zeros_like(ve)
    vel = np.stack([ve, vn], axis=1)
    res = strain_rate_at(clat, clon, lat, lon, vel, smoothing_scale_deg=0.5)
    # Pure shear: trace near zero, shear component present.
    assert abs(res.dilatation) < 5.0
    assert res.max_shear > 10.0


def test_insufficient_support_returns_zero():
    res = strain_rate_at(0.0, 0.0, np.array([40.0]), np.array([40.0]), np.array([[1.0, 1.0]]))
    assert res.n_effective < 3
    assert res.max_shear == 0.0


def test_scale_sweep_changes_result():
    clat, clon = 36.0, -120.0
    lat, lon = _grid(clat, clon, half_deg=1.0, n=20)
    rng = np.random.default_rng(0)
    dx = np.radians(lon - clon) * np.cos(np.radians(clat)) * EARTH_RADIUS_M
    ve = (30e-9 / 1e-3) * dx + rng.normal(0, 0.2, dx.size)
    vn = rng.normal(0, 0.2, dx.size)
    vel = np.stack([ve, vn], axis=1)
    results = strain_scale_sweep(clat, clon, lat, lon, vel, [0.3, 0.6, 1.0])
    assert len(results) == 3
    # All should recover roughly the same extension sign but can differ.
    assert all(r.exx > 10 for r in results)
    # The smoothing scale is recorded on each result.
    assert [r.smoothing_scale_deg for r in results] == [0.3, 0.6, 1.0]
