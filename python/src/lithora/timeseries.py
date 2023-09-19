"""Robust GNSS time-series velocity estimation (capability L11).

A station's daily position series is not a clean line. It has a linear trend
(the velocity we want), annual and semi-annual seasonal cycles, offsets from
equipment changes or earthquakes, and noise that is strongly correlated in
time. This module estimates the velocity with those features modelled
explicitly and, crucially, reports an uncertainty that does not pretend the
thousands of daily samples are independent.

Two estimators are provided:

* :func:`fit_trend_seasonal_offsets` -- a linear least-squares fit of
  intercept, trend, annual and semi-annual sine/cosine terms, and a step at
  each supplied offset epoch. This is the workhorse, and its formal standard
  error is inflated to account for temporal correlation (see below).
* :func:`midas_like_velocity` -- a robust pair-slope estimator in the spirit
  of the MIDAS method: the median of slopes between samples separated by whole
  years, which cancels the seasonal cycle and resists outliers and undetected
  steps. It gives a velocity that does not depend on a noise model at all.

The formal least-squares standard error of a trend from N daily samples with
white-noise assumptions is famously too small for geodetic series because the
noise is closer to flicker/random-walk. We scale the white-noise standard
error by an empirical factor derived from the lag-1 autocorrelation of the
residuals, which is a transparent and documented correction rather than a
hidden constant. It is an approximation, not a full stochastic-process
estimate, and is labelled as such.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

TWO_PI = 2.0 * np.pi


@dataclass
class TrendFit:
    velocity_mm_yr: float
    intercept_mm: float
    velocity_sigma_white_mm_yr: float
    velocity_sigma_inflated_mm_yr: float
    lag1_autocorr: float
    n_samples: int
    seasonal_amp_annual_mm: float
    n_offsets: int
    rms_residual_mm: float


def _design_matrix(t_years: np.ndarray, offset_epochs: list[float]) -> np.ndarray:
    """Build the design matrix columns: [1, t, sin/cos annual, sin/cos
    semiannual, step for each offset]."""
    cols = [np.ones_like(t_years), t_years]
    cols.append(np.sin(TWO_PI * t_years))
    cols.append(np.cos(TWO_PI * t_years))
    cols.append(np.sin(2 * TWO_PI * t_years))
    cols.append(np.cos(2 * TWO_PI * t_years))
    for ep in offset_epochs:
        cols.append((t_years >= ep).astype(float))
    return np.stack(cols, axis=1)


def fit_trend_seasonal_offsets(
    t_years: np.ndarray,
    pos_mm: np.ndarray,
    offset_epochs: list[float] | None = None,
) -> TrendFit:
    """Fit trend, seasonal terms, and offsets to one component of a series.

    ``t_years`` is decimal year, ``pos_mm`` is the position component in mm.
    The returned velocity is in mm/yr.
    """
    t = np.asarray(t_years, float)
    y = np.asarray(pos_mm, float)
    if t.size < 10:
        raise ValueError("need at least 10 samples for a seasonal trend fit")
    offsets = offset_epochs or []
    a = _design_matrix(t, offsets)
    coef, *_ = np.linalg.lstsq(a, y, rcond=None)
    resid = y - a @ coef
    dof = max(t.size - a.shape[1], 1)
    sigma2 = float(resid @ resid / dof)

    ata_inv = np.linalg.inv(a.T @ a)
    # Velocity is the second coefficient; its white-noise variance.
    var_white = sigma2 * ata_inv[1, 1]
    sigma_white = float(np.sqrt(max(var_white, 0.0)))

    # Lag-1 autocorrelation of residuals -> inflation factor
    # sqrt((1+r)/(1-r)) from the AR(1) effective-sample-size correction.
    r = _lag1_autocorr(resid)
    r_clamped = float(np.clip(r, 0.0, 0.999))
    inflation = np.sqrt((1.0 + r_clamped) / (1.0 - r_clamped))
    sigma_inflated = sigma_white * inflation

    annual_amp = float(np.hypot(coef[2], coef[3]))
    return TrendFit(
        velocity_mm_yr=float(coef[1]),
        intercept_mm=float(coef[0]),
        velocity_sigma_white_mm_yr=sigma_white,
        velocity_sigma_inflated_mm_yr=float(sigma_inflated),
        lag1_autocorr=r,
        n_samples=int(t.size),
        seasonal_amp_annual_mm=annual_amp,
        n_offsets=len(offsets),
        rms_residual_mm=float(np.sqrt(sigma2)),
    )


def _lag1_autocorr(x: np.ndarray) -> float:
    x = x - x.mean()
    denom = float(x @ x)
    if denom < 1e-30:
        return 0.0
    return float((x[:-1] @ x[1:]) / denom)


def midas_like_velocity(t_years: np.ndarray, pos_mm: np.ndarray) -> float:
    """Robust velocity as the median of one-year-separated pair slopes.

    Pairing samples about one year apart cancels the annual seasonal signal,
    and the median over all such pairs resists outliers and undetected steps.
    This is a deliberately model-free cross-check on the parametric fit. The
    returned velocity is in mm/yr.
    """
    t = np.asarray(t_years, float)
    y = np.asarray(pos_mm, float)
    order = np.argsort(t)
    t, y = t[order], y[order]
    slopes = []
    j = 0
    for i in range(t.size):
        target = t[i] + 1.0
        while j < t.size and t[j] < target:
            j += 1
        if j >= t.size:
            break
        # Nearest sample at or after one year.
        dt = t[j] - t[i]
        if 0.9 < dt < 1.1:
            slopes.append((y[j] - y[i]) / dt)
    if not slopes:
        return float("nan")
    return float(np.median(slopes))
