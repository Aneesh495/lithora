"""Tests for station quality flags."""

import numpy as np

from lithora.quality import flag_stations


def test_short_record_flagged_and_ineligible():
    reports = flag_stations(
        ["A", "B"], duration_yr=np.array([2.0, 8.0]),
        sigma_mm_yr=np.array([0.5, 0.5]), speed_mm_yr=np.array([15.0, 15.0]),
    )
    assert "short_record" in reports[0].flags and not reports[0].eligible
    assert reports[1].eligible


def test_implausible_speed_flagged_and_ineligible():
    reports = flag_stations(
        ["A"], duration_yr=np.array([10.0]),
        sigma_mm_yr=np.array([0.5]), speed_mm_yr=np.array([1056.0]),
    )
    assert "implausible_speed" in reports[0].flags
    assert not reports[0].eligible


def test_high_uncertainty_is_descriptive_not_disqualifying():
    reports = flag_stations(
        ["A"], duration_yr=np.array([10.0]),
        sigma_mm_yr=np.array([5.0]), speed_mm_yr=np.array([15.0]),
    )
    assert "high_uncertainty" in reports[0].flags
    # High uncertainty alone does not make a station ineligible.
    assert reports[0].eligible


def test_clean_station_has_no_flags():
    reports = flag_stations(
        ["A"], duration_yr=np.array([12.0]),
        sigma_mm_yr=np.array([0.4]), speed_mm_yr=np.array([20.0]),
    )
    assert reports[0].flags == []
    assert reports[0].eligible
