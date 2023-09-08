"""Weighted rigid Euler-pole fitting from station velocities.

Given a set of GNSS stations on one presumed-rigid plate, each with a
horizontal velocity (east, north) in mm/yr and optionally a 2x2 covariance,
we estimate the single Euler vector ``omega`` that best explains them under
rigid rotation ``v = omega x r``.

The key observation is that this is *linear* in ``omega``. Writing the
surface velocity at station ``i`` as ``v_i = omega x r_i`` and projecting onto
the local east/north basis gives two linear equations per station:

    [ v_e ]   [ (e_i . (. x r_i)) ]
    [ v_n ] = [ (n_i . (. x r_i)) ] omega

where ``e_i``, ``n_i`` are the east/north unit vectors. Stacking all stations
yields ``A omega = d`` which we solve by weighted least squares with the
inverse velocity covariance as the weight. This gives both the estimate and
its covariance, from which an uncertainty ellipse for the pole follows.

We check conditioning explicitly: clustered stations or a nearly colinear
network leave the rotation axis poorly constrained, and we surface that as a
high condition number and inflated covariance rather than a confident wrong
pole. This directly supports capability L13 and the identifiability diagnostics
of L14.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .sphere import EARTH_RADIUS_M, latlon_to_unit, local_enu_basis


@dataclass
class EulerFit:
    """Result of a rigid Euler-pole fit.

    Attributes
    ----------
    omega:
        Estimated Euler vector in rad/Myr, shape ``(3,)``.
    omega_cov:
        3x3 covariance of ``omega`` in (rad/Myr)^2.
    pole_lat_deg, pole_lon_deg:
        Euler pole location (axis direction) in degrees.
    rate_deg_per_myr:
        Rotation rate magnitude in degrees per million years.
    condition_number:
        Condition number of the weighted normal matrix. Large values warn of
        a poorly constrained axis (clustered or colinear stations).
    rank_deficient:
        True when the normal matrix is effectively singular.
    n_stations:
        Number of stations used.
    weighted_rms_mm_yr:
        Weighted RMS of the velocity residuals in mm/yr.
    """

    omega: np.ndarray
    omega_cov: np.ndarray
    pole_lat_deg: float
    pole_lon_deg: float
    rate_deg_per_myr: float
    condition_number: float
    rank_deficient: bool
    n_stations: int
    weighted_rms_mm_yr: float


def _safe_inverse_2x2(cov: np.ndarray) -> np.ndarray:
    """Invert a 2x2 velocity covariance, degrading gracefully.

    A zero or singular covariance (which happens for noise-free synthetic
    data, or a record with no reported uncertainty) cannot be inverted to a
    weight. Rather than crash or silently fabricate a tight weight, we fall
    back to an identity weight, which treats that station's two components as
    equally and unit weighted. Callers that need calibrated uncertainty must
    supply a proper positive-definite covariance.
    """
    det = cov[0, 0] * cov[1, 1] - cov[0, 1] * cov[1, 0]
    if not np.isfinite(det) or abs(det) < 1e-12:
        return np.eye(2)
    return np.linalg.inv(cov)


def _cross_operator(r: np.ndarray) -> np.ndarray:
    """Skew matrix ``[r]_x`` so that ``[r]_x omega = r x omega``.

    Note ``omega x r = -(r x omega) = -[r]_x omega``, so the design rows use
    ``-[r]_x`` projected onto east/north.
    """
    x, y, z = r
    return np.array([[0.0, -z, y], [z, 0.0, -x], [-y, x, 0.0]])


def fit_euler_pole(
    lat_deg: np.ndarray,
    lon_deg: np.ndarray,
    vel_en_mm_yr: np.ndarray,
    cov_en_mm_yr: np.ndarray | None = None,
    cond_warn: float = 1e8,
) -> EulerFit:
    """Fit an Euler pole to station velocities by weighted least squares.

    Parameters
    ----------
    lat_deg, lon_deg:
        Station coordinates, shape ``(n,)``.
    vel_en_mm_yr:
        Horizontal velocities (east, north) in mm/yr, shape ``(n, 2)``.
    cov_en_mm_yr:
        Optional per-station 2x2 velocity covariance, shape ``(n, 2, 2)``.
        When omitted, an identity weight is used and the reported covariance
        is purely formal (do not read it as a calibrated geodetic uncertainty).
    cond_warn:
        Condition number above which the axis is flagged poorly constrained.
    """
    lat = np.asarray(lat_deg, dtype=float).reshape(-1)
    lon = np.asarray(lon_deg, dtype=float).reshape(-1)
    vel = np.asarray(vel_en_mm_yr, dtype=float).reshape(-1, 2)
    n = lat.size
    if n < 2:
        raise ValueError("need at least 2 stations to constrain an Euler pole")

    r = latlon_to_unit(lat, lon)  # (n, 3)
    east, north, _ = local_enu_basis(lat, lon)

    # Build design matrix A (2n x 3) and data vector d (2n,).
    # v = omega x r = -[r]_x omega. Convert the unit-radius rad/Myr velocity
    # to mm/yr by the factor R * 1e-3 so the fit works in observed units.
    scale = EARTH_RADIUS_M * 1e-3  # unit-rad/Myr cross magnitude -> mm/yr
    rows = []
    data = []
    weights = []
    for i in range(n):
        cross = -_cross_operator(r[i]) * scale  # 3x3 mapping omega -> cart vel (mm/yr)
        row_e = east[i] @ cross
        row_n = north[i] @ cross
        rows.append(row_e)
        rows.append(row_n)
        data.append(vel[i, 0])
        data.append(vel[i, 1])
        if cov_en_mm_yr is not None:
            w = _safe_inverse_2x2(np.asarray(cov_en_mm_yr[i], dtype=float))
        else:
            w = np.eye(2)
        weights.append(w)

    a = np.array(rows)  # (2n, 3)
    d = np.array(data)  # (2n,)

    # Block-diagonal weight application: build W-weighted normal equations.
    ata = np.zeros((3, 3))
    atd = np.zeros(3)
    for i in range(n):
        ai = a[2 * i : 2 * i + 2, :]  # (2,3)
        di = d[2 * i : 2 * i + 2]  # (2,)
        wi = weights[i]  # (2,2)
        ata += ai.T @ wi @ ai
        atd += ai.T @ wi @ di

    # Conditioning and solve.
    eigvals = np.linalg.eigvalsh(ata)
    eigvals = np.clip(eigvals, 0.0, None)
    cond = float(eigvals.max() / eigvals.min()) if eigvals.min() > 0 else np.inf
    rank_deficient = not np.isfinite(cond) or cond > 1e14

    if rank_deficient:
        omega = np.linalg.lstsq(ata, atd, rcond=None)[0]
        omega_cov = np.full((3, 3), np.nan)
    else:
        ata_inv = np.linalg.inv(ata)
        omega = ata_inv @ atd
        omega_cov = ata_inv  # covariance under unit-variance weighted residuals

    # Residuals and weighted RMS.
    resid = d - a @ omega
    wsum = 0.0
    dof = max(2 * n - 3, 1)
    for i in range(n):
        ri = resid[2 * i : 2 * i + 2]
        wsum += ri @ weights[i] @ ri
    weighted_rms = float(np.sqrt(wsum / dof))

    # Rescale covariance by the reduced chi-square so it reflects observed
    # scatter when weights are only relative.
    if not rank_deficient:
        omega_cov = omega_cov * (wsum / dof)

    axis_norm = float(np.linalg.norm(omega))
    if axis_norm > 0:
        axis = omega / axis_norm
        pole_lat = float(np.degrees(np.arcsin(np.clip(axis[2], -1, 1))))
        pole_lon = float(np.degrees(np.arctan2(axis[1], axis[0])))
    else:
        pole_lat = pole_lon = 0.0
    rate_deg = float(np.degrees(axis_norm))

    return EulerFit(
        omega=omega,
        omega_cov=omega_cov,
        pole_lat_deg=pole_lat,
        pole_lon_deg=pole_lon,
        rate_deg_per_myr=rate_deg,
        condition_number=cond,
        rank_deficient=rank_deficient,
        n_stations=n,
        weighted_rms_mm_yr=weighted_rms,
    )


def predict_velocities(omega: np.ndarray, lat_deg: np.ndarray, lon_deg: np.ndarray) -> np.ndarray:
    """Predict (east, north) mm/yr velocities for an Euler vector at stations."""
    from .sphere import cartesian_velocity_to_enu, euler_velocity

    r = latlon_to_unit(lat_deg, lon_deg)
    v_cart_unit = euler_velocity(omega, r)  # rad/Myr at unit radius
    v_cart_mm = v_cart_unit * EARTH_RADIUS_M * 1e-3
    return cartesian_velocity_to_enu(v_cart_mm, lat_deg, lon_deg)
