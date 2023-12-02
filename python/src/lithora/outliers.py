"""Residual outlier investigation with provenance (capability L22).

After removing the rigid Euler-pole motion, a few stations have residuals far
larger than their neighbours. These are worth investigating, but a large
residual is not automatically a geological signal: it can be an equipment
change, a nearby earthquake offset, a short or gappy record, or a local
monument instability. This module flags residual outliers robustly and attaches
the station's provenance (record duration, uncertainty) so a human can
investigate, rather than drawing an automatic geological conclusion.

Outliers are flagged by a robust z-score (median and median absolute deviation)
of the residual speed, which resists the very outliers it is detecting. The
module deliberately does not classify a cause; it surfaces candidates and their
metadata.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .euler_fit import fit_euler_pole, predict_velocities


@dataclass
class ResidualOutlier:
    station_id: str
    lat: float
    lon: float
    residual_speed_mm_yr: float
    robust_z: float
    duration_yr: float
    sigma_mm_yr: float
    note: str


def investigate_residuals(
    station_ids: list[str],
    lat: np.ndarray,
    lon: np.ndarray,
    vel_en: np.ndarray,
    cov_en: np.ndarray,
    duration_yr: np.ndarray,
    z_threshold: float = 4.0,
) -> list[ResidualOutlier]:
    """Flag residual outliers after a rigid fit, with provenance attached.

    Returns the flagged stations sorted by descending robust z-score. The
    ``note`` field suggests benign explanations to check first, in keeping with
    not jumping to a geological conclusion.
    """
    lat = np.asarray(lat, float).reshape(-1)
    lon = np.asarray(lon, float).reshape(-1)
    vel = np.asarray(vel_en, float).reshape(-1, 2)
    dur = np.asarray(duration_yr, float).reshape(-1)

    fit = fit_euler_pole(lat, lon, vel, cov_en)
    pred = predict_velocities(fit.omega, lat, lon)
    resid_speed = np.linalg.norm(vel - pred, axis=1)

    med = np.median(resid_speed)
    mad = np.median(np.abs(resid_speed - med))
    # 1.4826 scales MAD to a standard-deviation estimate for normal data.
    scale = 1.4826 * mad if mad > 1e-9 else (np.std(resid_speed) + 1e-9)
    z = (resid_speed - med) / scale

    sig = np.sqrt(0.5 * (np.asarray(cov_en)[:, 0, 0] + np.asarray(cov_en)[:, 1, 1]))

    out: list[ResidualOutlier] = []
    for i in range(lat.size):
        if z[i] >= z_threshold:
            notes = []
            if dur[i] < 5.0:
                notes.append("short record")
            if sig[i] > 2.0 * np.median(sig):
                notes.append("high reported uncertainty")
            note = "; ".join(notes) if notes else "check for offsets, nearby events, monument issues"
            out.append(
                ResidualOutlier(
                    station_id=station_ids[i],
                    lat=float(lat[i]),
                    lon=float(lon[i]),
                    residual_speed_mm_yr=float(resid_speed[i]),
                    robust_z=float(z[i]),
                    duration_yr=float(dur[i]),
                    sigma_mm_yr=float(sig[i]),
                    note=note,
                )
            )
    out.sort(key=lambda o: o.robust_z, reverse=True)
    return out
