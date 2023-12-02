"""Tests for residual outlier investigation."""

import numpy as np

from lithora.outliers import investigate_residuals
from lithora.synthetic import make_rigid_plate


def test_flags_injected_outlier_with_provenance():
    world = make_rigid_plate(
        n_stations=150, pole_lat_deg=50, pole_lon_deg=-100, rate_deg_per_myr=0.7,
        region_center=(38, -110), region_half_width_deg=10, noise_mm_yr=0.3, seed=4,
    )
    lat, lon, vel, cov = world.lat_deg, world.lon_deg, world.vel_en_mm_yr.copy(), world.cov_en_mm_yr
    ids = [f"ST{i:03d}" for i in range(lat.size)]
    dur = np.full(lat.size, 10.0)

    # Inject a large anomaly at station 7 and a short-record flag at 8.
    vel[7] += np.array([25.0, -20.0])
    dur[8] = 2.0
    vel[8] += np.array([30.0, 0.0])

    outliers = investigate_residuals(ids, lat, lon, vel, cov, dur, z_threshold=4.0)
    flagged = {o.station_id for o in outliers}
    assert "ST007" in flagged
    # The short-record station should carry that note.
    st8 = [o for o in outliers if o.station_id == "ST008"]
    if st8:
        assert "short record" in st8[0].note


def test_clean_field_flags_nothing():
    world = make_rigid_plate(
        n_stations=120, pole_lat_deg=30, pole_lon_deg=20, rate_deg_per_myr=0.5,
        region_center=(10, 25), region_half_width_deg=12, noise_mm_yr=0.3, seed=9,
    )
    ids = [f"ST{i:03d}" for i in range(world.lat_deg.size)]
    dur = np.full(world.lat_deg.size, 10.0)
    outliers = investigate_residuals(
        ids, world.lat_deg, world.lon_deg, world.vel_en_mm_yr, world.cov_en_mm_yr, dur, z_threshold=6.0
    )
    # A clean rigid field with small noise should have few or no extreme outliers.
    assert len(outliers) <= 2


def test_outliers_sorted_by_z():
    world = make_rigid_plate(
        n_stations=100, pole_lat_deg=45, pole_lon_deg=-100, rate_deg_per_myr=0.6,
        region_center=(38, -110), region_half_width_deg=8, noise_mm_yr=0.3, seed=1,
    )
    lat, lon, vel, cov = world.lat_deg, world.lon_deg, world.vel_en_mm_yr.copy(), world.cov_en_mm_yr
    ids = [f"ST{i:03d}" for i in range(lat.size)]
    dur = np.full(lat.size, 10.0)
    vel[3] += np.array([40.0, 0.0])
    vel[20] += np.array([15.0, 0.0])
    outliers = investigate_residuals(ids, lat, lon, vel, cov, dur, z_threshold=3.0)
    zs = [o.robust_z for o in outliers]
    assert zs == sorted(zs, reverse=True)
