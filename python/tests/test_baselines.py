"""Tests for deterministic baselines, GP, and spatial evaluation."""

import numpy as np

from lithora.baselines import LocalRegression, NearestNeighbor, RigidOnly, great_circle_angles
from lithora.evaluate import (
    distance_to_training,
    spatial_block_folds,
    velocity_metrics,
)
from lithora.gp import GPResidual
from lithora.synthetic import make_rigid_plate


def _world():
    return make_rigid_plate(
        n_stations=200,
        pole_lat_deg=50.0,
        pole_lon_deg=-100.0,
        rate_deg_per_myr=0.7,
        region_center=(38.0, -115.0),
        region_half_width_deg=12.0,
        noise_mm_yr=0.4,
        seed=11,
        deform_fraction=0.3,
        deform_amp_mm_yr=4.0,
    )


def test_great_circle_angles_symmetry_and_zero_diagonal():
    lat = np.array([0.0, 10.0, -20.0])
    lon = np.array([0.0, 40.0, 100.0])
    d = great_circle_angles(lat, lon, lat, lon)
    assert np.allclose(np.diag(d), 0.0, atol=1e-12)
    assert np.allclose(d, d.T, atol=1e-12)


def test_rigid_only_predicts_rigid_part():
    w = _world()
    model = RigidOnly.fit(w.lat_deg, w.lon_deg, w.vel_en_mm_yr, w.cov_en_mm_yr)
    pred = model.predict(w.lat_deg, w.lon_deg)
    # In the rigid interior (not deforming), prediction should be close to truth.
    interior = ~w.in_deforming_zone
    err = np.linalg.norm(pred[interior] - w.truth_vel_en_mm_yr[interior], axis=1)
    assert np.median(err) < 1.0


def test_nn_reproduces_training_velocity_at_training_points():
    w = _world()
    model = NearestNeighbor.fit(w.lat_deg, w.lon_deg, w.vel_en_mm_yr, w.cov_en_mm_yr)
    pred = model.predict(w.lat_deg, w.lon_deg)
    # At a training station the nearest neighbor is itself.
    assert np.allclose(pred, w.vel_en_mm_yr, atol=1e-6)


def test_local_regression_beats_rigid_in_deforming_zone():
    w = _world()
    rigid = RigidOnly.fit(w.lat_deg, w.lon_deg, w.vel_en_mm_yr, w.cov_en_mm_yr)
    local = LocalRegression.fit(w.lat_deg, w.lon_deg, w.vel_en_mm_yr, w.cov_en_mm_yr, bandwidth_deg=3.0)
    zone = w.in_deforming_zone
    # Evaluate against noise-free truth in the deforming zone.
    rigid_err = np.linalg.norm(rigid.predict(w.lat_deg[zone], w.lon_deg[zone]) - w.truth_vel_en_mm_yr[zone], axis=1)
    local_err = np.linalg.norm(local.predict(w.lat_deg[zone], w.lon_deg[zone]) - w.truth_vel_en_mm_yr[zone], axis=1)
    assert np.median(local_err) < np.median(rigid_err)


def test_gp_returns_std_and_is_finite():
    w = _world()
    gp = GPResidual.fit(w.lat_deg, w.lon_deg, w.vel_en_mm_yr, w.cov_en_mm_yr)
    pred, std = gp.predict(w.lat_deg, w.lon_deg, return_std=True)
    assert pred.shape == (w.lat_deg.size, 2)
    assert np.all(np.isfinite(std)) and np.all(std > 0)


def test_spatial_folds_respect_buffer():
    w = _world()
    folds = spatial_block_folds(w.lat_deg, w.lon_deg, n_folds=5, buffer_deg=1.0, seed=2)
    assert len(folds) >= 2
    for f in folds:
        if f.train_idx.size == 0 or f.test_idx.size == 0:
            continue
        d = great_circle_angles(
            w.lat_deg[f.test_idx], w.lon_deg[f.test_idx],
            w.lat_deg[f.train_idx], w.lon_deg[f.train_idx],
        )
        # No training station within the buffer of any test station.
        assert np.degrees(d.min()) > 1.0 - 1e-6


def test_metrics_basic_properties():
    pred = np.array([[1.0, 0.0], [0.0, 2.0]])
    true = np.array([[1.0, 0.0], [0.0, 1.0]])
    m = velocity_metrics(pred, true)
    assert abs(m.vector_rmse - np.sqrt(0.5)) < 1e-9
    assert m.n == 2


def test_distance_to_training():
    lat_t = np.array([0.0, 10.0])
    lon_t = np.array([0.0, 0.0])
    d = distance_to_training(np.array([5.0]), np.array([0.0]), lat_t, lon_t)
    assert np.degrees(d[0]) > 4.0 and np.degrees(d[0]) < 6.0
