"""A covariance-aware Gaussian-process baseline for the residual field (L15).

This fits an independent GP to each horizontal residual component (east,
north) using a squared-exponential kernel over great-circle distance. Unlike
the local regression, the GP gives a predictive variance, so it is the natural
calibrated non-learned reference for the uncertainty comparisons (G08).

The implementation is deliberately small and exact: it forms the training
kernel, adds the per-station observation noise (from the supplied velocity
covariance, or a floor when none is given), and solves with a Cholesky factor.
It is not meant to scale to the full network at once; evaluation uses it on
spatial folds of a few hundred stations where an exact GP is appropriate.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .baselines import great_circle_angles
from .euler_fit import fit_euler_pole, predict_velocities


@dataclass
class GPResidual:
    """Independent per-component GP over the rigid residual field."""

    omega: np.ndarray
    lat: np.ndarray
    lon: np.ndarray
    residual_en: np.ndarray
    length_scale_rad: float
    signal_var: float
    noise_var: float
    _alpha: np.ndarray  # (nt, 2) precomputed K^-1 y per component
    _l: np.ndarray  # Cholesky factor of K (shared, since noise is scalar here)

    @classmethod
    def fit(
        cls,
        lat,
        lon,
        vel_en,
        cov_en=None,
        length_scale_deg: float = 4.0,
        signal_std_mm_yr: float = 2.0,
        noise_floor_mm_yr: float = 0.5,
    ) -> "GPResidual":
        f = fit_euler_pole(lat, lon, vel_en, cov_en)
        lat = np.asarray(lat, float).reshape(-1)
        lon = np.asarray(lon, float).reshape(-1)
        rigid = predict_velocities(f.omega, lat, lon)
        resid = np.asarray(vel_en, float).reshape(-1, 2) - rigid

        ls = np.radians(length_scale_deg)
        sv = signal_std_mm_yr**2
        if cov_en is not None:
            # Average the two diagonal variances as a scalar noise per station.
            cov = np.asarray(cov_en, float)
            noise = 0.5 * (cov[:, 0, 0] + cov[:, 1, 1])
            noise = np.maximum(noise, noise_floor_mm_yr**2)
        else:
            noise = np.full(lat.size, noise_floor_mm_yr**2)

        d = great_circle_angles(lat, lon, lat, lon)
        k = sv * np.exp(-0.5 * (d / ls) ** 2) + np.diag(noise)
        l = np.linalg.cholesky(k + 1e-9 * np.eye(lat.size))
        alpha = np.zeros((lat.size, 2))
        for comp in range(2):
            alpha[:, comp] = np.linalg.solve(l.T, np.linalg.solve(l, resid[:, comp]))

        return cls(
            omega=f.omega,
            lat=lat,
            lon=lon,
            residual_en=resid,
            length_scale_rad=ls,
            signal_var=sv,
            noise_var=float(np.mean(noise)),
            _alpha=alpha,
            _l=l,
        )

    def predict(self, lat_q, lon_q, return_std: bool = False):
        """Predict residual-corrected velocity, optionally with a std.

        Returns ``(n, 2)`` velocities, or ``(velocities, stds)`` when
        ``return_std`` is set. The std is per component in mm/yr.
        """
        lat_q = np.asarray(lat_q, float).reshape(-1)
        lon_q = np.asarray(lon_q, float).reshape(-1)
        rigid = predict_velocities(self.omega, lat_q, lon_q)
        d = great_circle_angles(lat_q, lon_q, self.lat, self.lon)  # (nq, nt)
        k_star = self.signal_var * np.exp(-0.5 * (d / self.length_scale_rad) ** 2)
        mean_resid = k_star @ self._alpha  # (nq, 2)
        out = rigid + mean_resid
        if not return_std:
            return out
        v = np.linalg.solve(self._l, k_star.T)  # (nt, nq)
        var = self.signal_var - np.sum(v * v, axis=0)
        var = np.clip(var, 0.0, None) + self.noise_var
        std = np.sqrt(var)[:, None].repeat(2, axis=1)
        return out, std
