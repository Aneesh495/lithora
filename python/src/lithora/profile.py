"""Regional cross-section profiles through a boundary (capability L29).

A standard way to read deformation across a plate boundary is to sample the
velocity field along a transect perpendicular to the boundary and plot the
boundary-parallel and boundary-perpendicular components against distance. A
sharp step in the parallel component marks a locked or slipping fault; a ramp
marks distributed shear. This module builds such a profile from a station
velocity field, with the sampling resolution and any gaps reported so the
profile is never read as denser than the data support.

The profile is computed by projecting each nearby station onto the transect
line and binning by along-profile distance, weighting by perpendicular distance
to the line so only stations close to the transect contribute. This keeps the
profile honest about where there is and is not data.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .sphere import EARTH_RADIUS_M, latlon_to_unit, local_enu_basis


@dataclass
class ProfileBin:
    along_km: float
    n_stations: int
    mean_parallel_mm_yr: float
    mean_perp_mm_yr: float
    std_parallel_mm_yr: float


@dataclass
class Profile:
    start: tuple[float, float]
    end: tuple[float, float]
    length_km: float
    bin_width_km: float
    swath_half_width_km: float
    bins: list[ProfileBin]
    n_empty_bins: int


def _unit(v):
    n = np.linalg.norm(v)
    return v / n if n > 0 else v


def cross_section(
    lat: np.ndarray,
    lon: np.ndarray,
    vel_en: np.ndarray,
    start: tuple[float, float],
    end: tuple[float, float],
    bin_width_km: float = 20.0,
    swath_half_width_km: float = 40.0,
) -> Profile:
    """Build a velocity cross-section along the transect from start to end.

    ``start`` and ``end`` are (lat, lon) in degrees. Velocities are decomposed
    into components parallel and perpendicular to the transect azimuth. Bins
    with no stations within the swath are reported as empty rather than
    interpolated.
    """
    lat = np.asarray(lat, float).reshape(-1)
    lon = np.asarray(lon, float).reshape(-1)
    vel = np.asarray(vel_en, float).reshape(-1, 2)

    p0 = latlon_to_unit(np.array([start[0]]), np.array([start[1]]))[0]
    p1 = latlon_to_unit(np.array([end[0]]), np.array([end[1]]))[0]
    # Along-profile direction at the start, in the local tangent plane.
    east0, north0, _ = local_enu_basis(np.array([start[0]]), np.array([start[1]]))
    east0, north0 = east0[0], north0[0]
    chord = p1 - p0
    along_e = float(np.dot(chord, east0))
    along_n = float(np.dot(chord, north0))
    along_dir = _unit(np.array([along_e, along_n]))  # (east, north) unit
    perp_dir = np.array([-along_dir[1], along_dir[0]])  # rotate 90 deg

    # Transect length is the great-circle distance between the endpoints.
    length_km = float(np.arccos(np.clip(np.dot(p0, p1), -1, 1)) * EARTH_RADIUS_M / 1000.0)

    stations = latlon_to_unit(lat, lon)
    # Along and perpendicular offsets of each station from the start, in km,
    # using the local tangent plane at the start point.
    rel = stations - p0
    off_e = rel @ east0 * EARTH_RADIUS_M / 1000.0
    off_n = rel @ north0 * EARTH_RADIUS_M / 1000.0
    along_km = off_e * along_dir[0] + off_n * along_dir[1]
    perp_km = off_e * perp_dir[0] + off_n * perp_dir[1]

    # Decompose each station velocity into parallel/perpendicular components.
    v_par = vel[:, 0] * along_dir[0] + vel[:, 1] * along_dir[1]
    v_perp = vel[:, 0] * perp_dir[0] + vel[:, 1] * perp_dir[1]

    n_bins = max(1, int(np.ceil(length_km / bin_width_km)))
    bins: list[ProfileBin] = []
    n_empty = 0
    for b in range(n_bins):
        lo = b * bin_width_km
        hi = lo + bin_width_km
        mask = (along_km >= lo) & (along_km < hi) & (np.abs(perp_km) <= swath_half_width_km)
        if not mask.any():
            n_empty += 1
            bins.append(ProfileBin(0.5 * (lo + hi), 0, float("nan"), float("nan"), float("nan")))
            continue
        bins.append(
            ProfileBin(
                along_km=0.5 * (lo + hi),
                n_stations=int(mask.sum()),
                mean_parallel_mm_yr=float(np.mean(v_par[mask])),
                mean_perp_mm_yr=float(np.mean(v_perp[mask])),
                std_parallel_mm_yr=float(np.std(v_par[mask])),
            )
        )

    return Profile(
        start=start,
        end=end,
        length_km=length_km,
        bin_width_km=bin_width_km,
        swath_half_width_km=swath_half_width_km,
        bins=bins,
        n_empty_bins=n_empty,
    )
