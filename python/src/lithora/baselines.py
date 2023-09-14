"""Deterministic deformation baselines (capability L15).

These are the non-learned predictors that any learned residual model must beat
to justify its complexity. All predict a horizontal velocity (east, north) in
mm/yr at a query location from a training set of stations:

* :class:`RigidOnly` predicts the best-fit rigid Euler-pole velocity
  everywhere. This is the null hypothesis: no deformation.
* :class:`NearestNeighbor` copies the velocity of the closest training
  station. It captures local structure but is discontinuous and blind to
  uncertainty.
* :class:`LocalRegression` fits a distance-weighted linear model of velocity
  in local tangent coordinates, a smooth interpolant with a bandwidth that
  trades bias against variance.

Distances are great-circle angles so the baselines are correct on the sphere,
not in a lat/lon plane that distorts near the poles. They operate on the
*residual* to the rigid fit so that each only has to model the deformation
part, which keeps them comparable to the learned residual model.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .euler_fit import fit_euler_pole, predict_velocities
from .sphere import latlon_to_unit


def great_circle_angles(
    lat_q: np.ndarray, lon_q: np.ndarray, lat_t: np.ndarray, lon_t: np.ndarray
) -> np.ndarray:
    """Great-circle angular distances (radians) between query and train points.

    Returns a matrix of shape ``(n_query, n_train)``.
    """
    q = latlon_to_unit(lat_q, lon_q).reshape(-1, 3)
    t = latlon_to_unit(lat_t, lon_t).reshape(-1, 3)
    dots = np.clip(q @ t.T, -1.0, 1.0)
    cross = np.linalg.norm(
        np.cross(q[:, None, :], t[None, :, :]), axis=-1
    )
    return np.arctan2(cross, dots)


@dataclass
class RigidOnly:
    """Best-fit rigid Euler pole; predicts the rigid velocity everywhere."""

    omega: np.ndarray

    @classmethod
    def fit(cls, lat, lon, vel_en, cov_en=None) -> "RigidOnly":
        f = fit_euler_pole(lat, lon, vel_en, cov_en)
        return cls(omega=f.omega)

    def predict(self, lat_q, lon_q) -> np.ndarray:
        return predict_velocities(self.omega, lat_q, lon_q)


@dataclass
class NearestNeighbor:
    """Nearest-neighbor residual predictor on top of a rigid fit."""

    omega: np.ndarray
    lat: np.ndarray
    lon: np.ndarray
    residual_en: np.ndarray

    @classmethod
    def fit(cls, lat, lon, vel_en, cov_en=None) -> "NearestNeighbor":
        f = fit_euler_pole(lat, lon, vel_en, cov_en)
        rigid = predict_velocities(f.omega, lat, lon)
        return cls(
            omega=f.omega,
            lat=np.asarray(lat, float).reshape(-1),
            lon=np.asarray(lon, float).reshape(-1),
            residual_en=np.asarray(vel_en, float).reshape(-1, 2) - rigid,
        )

    def predict(self, lat_q, lon_q) -> np.ndarray:
        rigid = predict_velocities(self.omega, lat_q, lon_q)
        d = great_circle_angles(lat_q, lon_q, self.lat, self.lon)
        idx = np.argmin(d, axis=1)
        return rigid + self.residual_en[idx]


@dataclass
class LocalRegression:
    """Distance-weighted local linear regression of the residual field.

    At each query point we fit ``residual ~ a + b * d_east + c * d_north`` in a
    local tangent frame, weighting training stations by a Gaussian of their
    great-circle distance with the given bandwidth (radians). This is smooth,
    adapts to local gradients, and reduces to a weighted mean when the local
    network is too small to fit the linear terms.
    """

    omega: np.ndarray
    lat: np.ndarray
    lon: np.ndarray
    residual_en: np.ndarray
    bandwidth_rad: float

    @classmethod
    def fit(cls, lat, lon, vel_en, cov_en=None, bandwidth_deg: float = 3.0) -> "LocalRegression":
        f = fit_euler_pole(lat, lon, vel_en, cov_en)
        rigid = predict_velocities(f.omega, lat, lon)
        return cls(
            omega=f.omega,
            lat=np.asarray(lat, float).reshape(-1),
            lon=np.asarray(lon, float).reshape(-1),
            residual_en=np.asarray(vel_en, float).reshape(-1, 2) - rigid,
            bandwidth_rad=np.radians(bandwidth_deg),
        )

    def predict(self, lat_q, lon_q) -> np.ndarray:
        lat_q = np.asarray(lat_q, float).reshape(-1)
        lon_q = np.asarray(lon_q, float).reshape(-1)
        rigid = predict_velocities(self.omega, lat_q, lon_q)
        d = great_circle_angles(lat_q, lon_q, self.lat, self.lon)  # (nq, nt)
        w = np.exp(-0.5 * (d / self.bandwidth_rad) ** 2)
        out = np.zeros((lat_q.size, 2))
        for i in range(lat_q.size):
            wi = w[i]
            if wi.sum() < 1e-12:
                continue  # no nearby stations: leave residual at zero
            # Local tangent offsets (approximate) in radians.
            d_east = np.radians(self.lon - lon_q[i]) * np.cos(np.radians(lat_q[i]))
            d_north = np.radians(self.lat - lat_q[i])
            design = np.stack([np.ones_like(d_east), d_east, d_north], axis=1)
            for comp in range(2):
                wd = wi[:, None] * design
                ata = design.T @ wd
                atb = design.T @ (wi * self.residual_en[:, comp])
                try:
                    coef = np.linalg.solve(ata + 1e-9 * np.eye(3), atb)
                    out[i, comp] = coef[0]  # intercept = value at the query
                except np.linalg.LinAlgError:
                    out[i, comp] = np.average(self.residual_en[:, comp], weights=wi)
        return rigid + out
