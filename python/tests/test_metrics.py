"""Focused tests for velocity metrics edge cases."""

import numpy as np

from lithora.evaluate import velocity_metrics


def test_perfect_prediction_has_zero_error():
    v = np.array([[3.0, 4.0], [1.0, 0.0]])
    m = velocity_metrics(v, v)
    assert m.vector_rmse == 0.0
    assert m.median_abs_error == 0.0


def test_direction_error_ignores_slow_stations():
    # A fast station with a flipped prediction, plus a near-zero station whose
    # direction is ill defined. The direction error should reflect only the
    # fast one.
    true = np.array([[10.0, 0.0], [0.05, 0.0]])
    pred = np.array([[-10.0, 0.0], [0.0, 0.05]])
    m = velocity_metrics(pred, true, speed_floor_mm_yr=1.0)
    # The fast station is reversed -> 180 degrees.
    assert abs(m.mean_direction_error_deg - 180.0) < 1.0


def test_coverage_reported_when_std_given():
    true = np.array([[0.0, 0.0], [0.0, 0.0]])
    pred = np.array([[0.5, 0.0], [2.0, 0.0]])
    std = np.array([[1.0, 1.0], [1.0, 1.0]])
    m = velocity_metrics(pred, true, std_en=std)
    # First station within 1 sigma in both components (east 0.5<=1), second
    # east 2.0 > 1 so out. Coverage counts components.
    assert m.coverage_1sigma is not None
    assert 0.0 <= m.coverage_1sigma <= 1.0
    assert m.mean_sharpness == 1.0


def test_error_versus_distance_bins():
    pred = np.zeros((8, 2))
    true = np.zeros((8, 2))
    true[:, 0] = np.arange(8)  # increasing error with index
    dist = np.radians(np.arange(8).astype(float))  # increasing distance
    m = velocity_metrics(pred, true, dist_to_train_rad=dist)
    assert len(m.error_vs_distance) == 4  # quartile bins
    # Error should increase with distance bin.
    errs = [e for _, e in m.error_vs_distance]
    assert errs == sorted(errs)
