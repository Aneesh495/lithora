"""Spatial evaluation: buffered folds and velocity metrics (L19, L20, G07, G08).

Honest evaluation of a spatial predictor must prevent a test station from
being predicted by a training station sitting a few kilometres away, which
would leak the answer. We build spatially buffered folds: the sphere is
partitioned into blocks, each fold holds out one block for testing, and any
training station within a buffer distance of a test station is dropped. The
buffer is what separates this from ordinary k-fold cross-validation and is
required for the coverage claims to mean anything under spatial correlation.

Metrics reported per fold and aggregated:

* vector RMSE in mm/yr (the Euclidean error of the east/north residual);
* directional error conditional on speed (ignored for near-zero velocities
  where direction is ill defined);
* robust error (median absolute error), less sensitive to a few outliers;
* interval coverage and sharpness when a predictor returns a std;
* error as a function of great-circle distance to the nearest training
  station, which exposes overconfident extrapolation into empty regions.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .baselines import great_circle_angles


@dataclass
class Fold:
    """One spatial fold: train and test index arrays into the full network."""

    train_idx: np.ndarray
    test_idx: np.ndarray
    dropped_to_buffer: int


def spatial_block_folds(
    lat: np.ndarray,
    lon: np.ndarray,
    n_folds: int = 5,
    buffer_deg: float = 1.0,
    seed: int = 0,
) -> list[Fold]:
    """Partition stations into ``n_folds`` spatial blocks with a buffer.

    Blocks are formed by k-means-like assignment to random seed centres on the
    sphere (a light, dependency-free clustering). For each fold the test set is
    one block; the train set is every other station *except* those within
    ``buffer_deg`` great-circle degrees of any test station.
    """
    lat = np.asarray(lat, float).reshape(-1)
    lon = np.asarray(lon, float).reshape(-1)
    n = lat.size
    rng = np.random.default_rng(seed)
    centre_idx = rng.choice(n, size=min(n_folds, n), replace=False)
    d_to_centres = great_circle_angles(lat, lon, lat[centre_idx], lon[centre_idx])
    assign = np.argmin(d_to_centres, axis=1)

    buffer_rad = np.radians(buffer_deg)
    folds: list[Fold] = []
    for b in range(len(centre_idx)):
        test_idx = np.where(assign == b)[0]
        if test_idx.size == 0:
            continue
        candidate_train = np.where(assign != b)[0]
        d = great_circle_angles(lat[candidate_train], lon[candidate_train], lat[test_idx], lon[test_idx])
        keep = d.min(axis=1) > buffer_rad
        train_idx = candidate_train[keep]
        folds.append(
            Fold(
                train_idx=train_idx,
                test_idx=test_idx,
                dropped_to_buffer=int((~keep).sum()),
            )
        )
    return folds


@dataclass
class VelocityMetrics:
    vector_rmse: float
    median_abs_error: float
    mean_direction_error_deg: float
    coverage_1sigma: float | None = None
    mean_sharpness: float | None = None
    n: int = 0
    error_vs_distance: list[tuple[float, float]] = field(default_factory=list)


def velocity_metrics(
    pred_en: np.ndarray,
    true_en: np.ndarray,
    std_en: np.ndarray | None = None,
    dist_to_train_rad: np.ndarray | None = None,
    speed_floor_mm_yr: float = 1.0,
) -> VelocityMetrics:
    """Compute velocity error metrics for one test set."""
    pred = np.asarray(pred_en, float).reshape(-1, 2)
    true = np.asarray(true_en, float).reshape(-1, 2)
    err = pred - true
    per_station = np.linalg.norm(err, axis=1)
    rmse = float(np.sqrt(np.mean(per_station**2)))
    mae = float(np.median(per_station))

    # Directional error only where the true speed is above the floor.
    speed = np.linalg.norm(true, axis=1)
    mask = speed > speed_floor_mm_yr
    if mask.any():
        dot = np.sum(pred[mask] * true[mask], axis=1)
        pn = np.linalg.norm(pred[mask], axis=1) * speed[mask]
        cos = np.clip(dot / np.maximum(pn, 1e-12), -1, 1)
        dir_err = float(np.degrees(np.mean(np.arccos(cos))))
    else:
        dir_err = float("nan")

    coverage = sharpness = None
    if std_en is not None:
        std = np.asarray(std_en, float).reshape(-1, 2)
        within = np.abs(err) <= std
        coverage = float(np.mean(within))
        sharpness = float(np.mean(std))

    evd: list[tuple[float, float]] = []
    if dist_to_train_rad is not None:
        d_deg = np.degrees(np.asarray(dist_to_train_rad, float).reshape(-1))
        order = np.argsort(d_deg)
        # Bin into quartiles of distance and report mean error per bin.
        bins = np.array_split(order, 4)
        for bi in bins:
            if bi.size:
                evd.append((float(np.mean(d_deg[bi])), float(np.mean(per_station[bi]))))

    return VelocityMetrics(
        vector_rmse=rmse,
        median_abs_error=mae,
        mean_direction_error_deg=dir_err,
        coverage_1sigma=coverage,
        mean_sharpness=sharpness,
        n=pred.shape[0],
        error_vs_distance=evd,
    )


def distance_to_training(lat_q, lon_q, lat_t, lon_t) -> np.ndarray:
    """Great-circle distance (radians) from each query to its nearest train."""
    d = great_circle_angles(lat_q, lon_q, lat_t, lon_t)
    return d.min(axis=1)
