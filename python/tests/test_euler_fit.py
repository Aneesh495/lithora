"""Tests for Euler-pole fitting, including synthetic recovery (gate G05)."""

import numpy as np

from lithora.euler_fit import fit_euler_pole, predict_velocities
from lithora.synthetic import make_rigid_plate


def test_recovers_known_pole_low_noise():
    world = make_rigid_plate(
        n_stations=120,
        pole_lat_deg=55.0,
        pole_lon_deg=-120.0,
        rate_deg_per_myr=0.8,
        region_center=(40.0, -110.0),
        region_half_width_deg=12.0,
        noise_mm_yr=0.3,
        seed=1,
    )
    fit = fit_euler_pole(world.lat_deg, world.lon_deg, world.vel_en_mm_yr, world.cov_en_mm_yr)
    err = np.linalg.norm(fit.omega - world.true_omega)
    true_mag = np.linalg.norm(world.true_omega)
    assert err / true_mag < 0.05, f"relative omega error {err / true_mag}"
    assert not fit.rank_deficient
    assert fit.weighted_rms_mm_yr < 3.0


def test_recovery_within_uncertainty_over_many_worlds():
    # Gate G05 flavour: across many simulated datasets, the true omega lies
    # within a few sigma of the estimate most of the time.
    inside = 0
    trials = 60
    for s in range(trials):
        world = make_rigid_plate(
            n_stations=80,
            pole_lat_deg=30.0,
            pole_lon_deg=20.0,
            rate_deg_per_myr=0.5,
            region_center=(10.0, 25.0),
            region_half_width_deg=15.0,
            noise_mm_yr=0.5,
            seed=100 + s,
        )
        fit = fit_euler_pole(world.lat_deg, world.lon_deg, world.vel_en_mm_yr, world.cov_en_mm_yr)
        if fit.rank_deficient:
            continue
        diff = fit.omega - world.true_omega
        # Mahalanobis distance under the estimated covariance.
        try:
            d2 = diff @ np.linalg.inv(fit.omega_cov) @ diff
        except np.linalg.LinAlgError:
            continue
        # 3 dof chi-square 99% quantile ~ 11.34.
        if d2 < 11.34:
            inside += 1
    # Expect the large majority inside the 99% region.
    assert inside >= int(0.8 * trials), f"only {inside}/{trials} inside"


def test_clustered_stations_are_ill_conditioned():
    # Stations packed into a tiny area leave the axis poorly constrained.
    world = make_rigid_plate(
        n_stations=50,
        pole_lat_deg=10.0,
        pole_lon_deg=10.0,
        rate_deg_per_myr=0.4,
        region_center=(0.0, 0.0),
        region_half_width_deg=0.05,  # ~5 km cluster
        noise_mm_yr=0.5,
        seed=7,
    )
    fit = fit_euler_pole(world.lat_deg, world.lon_deg, world.vel_en_mm_yr, world.cov_en_mm_yr)
    # The condition number should be far larger than for a spread network.
    assert fit.condition_number > 1e5


def test_predicted_velocities_match_fit():
    world = make_rigid_plate(
        n_stations=40,
        pole_lat_deg=-20.0,
        pole_lon_deg=140.0,
        rate_deg_per_myr=0.6,
        region_center=(-30.0, 135.0),
        region_half_width_deg=10.0,
        noise_mm_yr=0.0,
        seed=3,
    )
    fit = fit_euler_pole(world.lat_deg, world.lon_deg, world.vel_en_mm_yr, world.cov_en_mm_yr)
    pred = predict_velocities(fit.omega, world.lat_deg, world.lon_deg)
    # With zero noise the fit should reproduce the velocities closely.
    assert np.allclose(pred, world.vel_en_mm_yr, atol=0.05)
