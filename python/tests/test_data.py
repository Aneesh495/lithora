"""Offline tests for data parsers and time-series fitting.

These use captured samples of the real file formats so they run without
network access. The acquisition clients themselves are exercised separately
when a network is available.
"""

import numpy as np
import pytest

from lithora.data.ngl import GnssVelocityField, merge_same_frame, parse_midas
from lithora.data.usgs import parse_geojson
from lithora.timeseries import fit_trend_seasonal_offsets, midas_like_velocity

# Two real MIDAS IGS14 lines captured from geodesy.unr.edu (27 columns).
MIDAS_SAMPLE = (
    "0ABI MIDAS5 2009.4428 2024.7420 15.2992  5567  5532  10338   0.015129   0.014934   0.005377  "
    "0.000164 0.000165 0.000624    677.0499   7585405.3777  431.3223 0.080 0.072 0.059 "
    "0.002126 0.002142 0.008188   1  68.3543437805 -341.1835564059   431.36226\n"
    "0ABY MIDAS5 2015.2717 2024.7420  9.4703  3444  3409   6091   0.018483   0.013913   0.005170  "
    "0.000206 0.000186 0.000738  -1181.6560   6504674.0345   60.5048 0.046 0.047 0.056 "
    "0.002092 0.001883 0.007444   1  58.6589079158 -343.8203568940    60.52854\n"
)

# A trimmed USGS GeoJSON FeatureCollection with one event.
USGS_SAMPLE = (
    '{"type":"FeatureCollection","features":[{"type":"Feature","properties":'
    '{"mag":5.1,"place":"73 km WSW of Sado, Japan","time":1704102326217,'
    '"magType":"mb"},"geometry":{"type":"Point","coordinates":[137.5664,37.8107,10]},'
    '"id":"us6000m0yg"}]}'
)


def test_parse_midas_basic():
    field = parse_midas(MIDAS_SAMPLE, frame="IGS14")
    assert field.frame == "IGS14"
    assert len(field) == 2
    s = field.stations[0]
    assert s.station_id == "0ABI"
    # Longitude normalised from -341.18 to +18.82 ish.
    assert -180 < s.lon <= 180
    assert abs(s.lon - 18.8164) < 0.01
    # Velocity converted to mm/yr (0.015129 m/yr -> ~15.1 mm/yr).
    assert abs(s.ve_mm_yr - 15.129) < 0.01
    assert s.duration_yr > 15


def test_midas_eligibility_filter():
    field = parse_midas(MIDAS_SAMPLE, frame="IGS14")
    short = field.eligible(min_years=12.0)
    assert len(short) == 1  # only 0ABI has >12 years
    assert short.stations[0].station_id == "0ABI"


def test_merge_refuses_mixed_frames():
    a = parse_midas(MIDAS_SAMPLE, frame="IGS14")
    b = GnssVelocityField(frame="NA", stations=list(a.stations))
    with pytest.raises(ValueError, match="refusing to merge"):
        merge_same_frame([a, b])


def test_merge_same_frame_ok():
    a = parse_midas(MIDAS_SAMPLE, frame="IGS14")
    merged = merge_same_frame([a, a])
    assert len(merged) == 4


def test_unknown_frame_rejected():
    with pytest.raises(ValueError, match="unknown reference frame"):
        parse_midas(MIDAS_SAMPLE, frame="ZZ")


def test_parse_usgs_geojson():
    events = parse_geojson(USGS_SAMPLE)
    assert len(events) == 1
    e = events[0]
    assert e.event_id == "us6000m0yg"
    assert abs(e.lat - 37.8107) < 1e-4
    assert abs(e.lon - 137.5664) < 1e-4
    assert e.depth_km == 10
    assert e.mag_type == "mb"


def test_usgs_skips_null_magnitude():
    doc = (
        '{"type":"FeatureCollection","features":[{"type":"Feature","properties":'
        '{"mag":null,"time":1,"magType":"mb"},"geometry":{"coordinates":[0,0,0]},"id":"x"}]}'
    )
    assert parse_geojson(doc) == []


def test_trend_recovers_known_velocity():
    # Build a synthetic daily series: 20 mm/yr trend + annual cycle + noise.
    rng = np.random.default_rng(0)
    t = 2010 + np.arange(0, 365 * 8) / 365.25
    true_v = 20.0
    y = 5.0 + true_v * (t - t[0]) + 3.0 * np.sin(2 * np.pi * t) + rng.normal(0, 1.0, t.size)
    fit = fit_trend_seasonal_offsets(t, y)
    assert abs(fit.velocity_mm_yr - true_v) < 0.5
    # Inflated uncertainty must be at least the white-noise one.
    assert fit.velocity_sigma_inflated_mm_yr >= fit.velocity_sigma_white_mm_yr
    assert fit.seasonal_amp_annual_mm > 2.0


def test_trend_handles_offset():
    rng = np.random.default_rng(1)
    t = 2010 + np.arange(0, 365 * 6) / 365.25
    y = 10.0 * (t - t[0]) + rng.normal(0, 0.5, t.size)
    # Inject a 15 mm step at the midpoint epoch.
    step_epoch = t[t.size // 2]
    y += 15.0 * (t >= step_epoch)
    fit = fit_trend_seasonal_offsets(t, y, offset_epochs=[step_epoch])
    # Trend should still be ~10 mm/yr despite the step.
    assert abs(fit.velocity_mm_yr - 10.0) < 0.5
    assert fit.n_offsets == 1


def test_midas_like_cross_check():
    rng = np.random.default_rng(2)
    t = 2010 + np.arange(0, 365 * 7) / 365.25
    y = 12.0 * (t - t[0]) + 4.0 * np.sin(2 * np.pi * t) + rng.normal(0, 1.0, t.size)
    v = midas_like_velocity(t, y)
    assert abs(v - 12.0) < 1.0
