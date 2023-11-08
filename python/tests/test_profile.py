"""Tests for the cross-section profile against a synthetic fault."""

import numpy as np

from lithora.profile import cross_section


def test_profile_recovers_fault_parallel_step():
    # Build stations in a box with a boundary-parallel velocity step across a
    # north-south fault at lon = -120. West side +20 mm/yr north, east side 0.
    rng = np.random.default_rng(0)
    lat = rng.uniform(34, 38, 400)
    lon = rng.uniform(-122, -118, 400)
    vn = np.where(lon < -120.0, 20.0, 0.0)
    ve = np.zeros_like(vn)
    vel = np.stack([ve, vn], axis=1)

    # Transect west-to-east across the fault at latitude 36.
    prof = cross_section(lat, lon, vel, start=(36.0, -122.0), end=(36.0, -118.0),
                         bin_width_km=25.0, swath_half_width_km=60.0)

    # The along-profile direction is east; the fault step is in the north
    # (boundary-parallel) component. Early bins (west) should show ~20, late
    # bins (east) ~0 in the perpendicular (north) component.
    filled = [b for b in prof.bins if b.n_stations > 0]
    assert len(filled) >= 4
    west = filled[0]
    east = filled[-1]
    # One side near 20, the other near 0 in the perpendicular component.
    assert abs(west.mean_perp_mm_yr - 20.0) < 5.0 or abs(west.mean_perp_mm_yr) < 5.0
    assert abs(east.mean_perp_mm_yr - 20.0) < 5.0 or abs(east.mean_perp_mm_yr) < 5.0
    # And the two ends differ (there is a step).
    assert abs(west.mean_perp_mm_yr - east.mean_perp_mm_yr) > 10.0


def test_profile_reports_empty_bins():
    # A transect through empty space should report empty bins, not interpolate.
    lat = np.array([36.0, 36.1])
    lon = np.array([-120.0, -120.1])
    vel = np.array([[1.0, 1.0], [1.0, 1.0]])
    prof = cross_section(lat, lon, vel, start=(0.0, 0.0), end=(0.0, 5.0), bin_width_km=50.0)
    assert prof.n_empty_bins == len(prof.bins)
    assert all(np.isnan(b.mean_parallel_mm_yr) for b in prof.bins)


def test_profile_length_matches_great_circle():
    # 5 degrees of longitude at the equator is about 556 km.
    prof = cross_section(
        np.array([0.0]), np.array([0.0]), np.array([[0.0, 0.0]]),
        start=(0.0, 0.0), end=(0.0, 5.0),
    )
    assert abs(prof.length_km - 556.0) < 5.0
