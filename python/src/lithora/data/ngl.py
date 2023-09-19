"""Nevada Geodetic Laboratory (NGL) GNSS velocity acquisition (L10, L12).

NGL publishes MIDAS robust-trend station velocities in several reference
frames. We parse the MIDAS velocity file format and keep the reference frame
as a first-class attribute, because mixing frames silently (IGS14 vs a
plate-fixed frame, or IGS14 vs IGS20) produces velocities that look fine and
are wrong. A :class:`GnssVelocityField` refuses to merge records from
different frames.

Reference and citation (attach in any publication of results):
Blewitt, G., C. Kreemer, W. C. Hammond, and J. Gazeaux (2016), MIDAS robust
trend estimator for accurate GPS station velocities without step detection,
J. Geophys. Res. Solid Earth, 121, doi:10.1002/2015JB012552.

Column layout of the MIDAS file (see the NGL readme):
  1    station id (4 char)
  3-4  first/last epoch (decimal year)
  5    duration (years)
  9-11 east, north, up velocity (m/yr)
  12-14 east, north, up velocity uncertainty (m/yr)
  25-27 latitude, longitude (deg), height (m)

We convert velocities to mm/yr on load and expose the duration so the
five-year eligibility rule (and other quality flags) can be applied
downstream without re-reading the file.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

# Map the NGL reference-frame code to a human label and whether it is a global
# (non plate-fixed) frame. Only the codes we actually support are listed.
KNOWN_FRAMES = {
    "IGS14": "IGS14 global frame",
    "IGS20": "IGS20 global frame",
    "NA": "North America fixed",
    "EU": "Eurasia fixed",
    "PA": "Pacific fixed",
    "AU": "Australia fixed",
    "SA": "South America fixed",
    "AF": "Africa fixed",
    "AN": "Antarctica fixed",
    "AR": "Arabia fixed",
    "NZ": "Nazca fixed",
}

M_TO_MM = 1000.0


@dataclass
class GnssStation:
    station_id: str
    lat: float
    lon: float
    height_m: float
    ve_mm_yr: float
    vn_mm_yr: float
    vu_mm_yr: float
    sve_mm_yr: float
    svn_mm_yr: float
    svu_mm_yr: float
    first_epoch: float
    last_epoch: float
    duration_yr: float


@dataclass
class GnssVelocityField:
    """A set of station velocities all in one reference frame."""

    frame: str
    stations: list[GnssStation]
    source: str = "Nevada Geodetic Laboratory MIDAS"
    citation: str = "Blewitt et al. (2016), doi:10.1002/2015JB012552"
    provenance: dict = field(default_factory=dict)

    def __len__(self) -> int:
        return len(self.stations)

    def eligible(self, min_years: float = 5.0) -> "GnssVelocityField":
        """Return a copy keeping only stations with at least ``min_years`` of
        observations. This freezes the eligibility rule explicitly rather than
        filtering implicitly elsewhere."""
        kept = [s for s in self.stations if s.duration_yr >= min_years]
        return GnssVelocityField(
            frame=self.frame,
            stations=kept,
            source=self.source,
            citation=self.citation,
            provenance={**self.provenance, "eligibility_min_years": min_years, "n_after": len(kept)},
        )

    def arrays(self) -> dict:
        """Return column arrays for fitting: lat, lon, vel_en (mm/yr),
        cov_en (diagonal mm/yr^2), and duration."""
        lat = np.array([s.lat for s in self.stations])
        lon = np.array([s.lon for s in self.stations])
        vel = np.array([[s.ve_mm_yr, s.vn_mm_yr] for s in self.stations])
        cov = np.array(
            [np.diag([max(s.sve_mm_yr, 1e-6) ** 2, max(s.svn_mm_yr, 1e-6) ** 2]) for s in self.stations]
        )
        dur = np.array([s.duration_yr for s in self.stations])
        return {"lat": lat, "lon": lon, "vel_en": vel, "cov_en": cov, "duration_yr": dur}


def normalize_lon(lon_deg: float) -> float:
    """NGL longitudes can run 0..360; normalise to (-180, 180]."""
    l = (lon_deg + 180.0) % 360.0 - 180.0
    return l + 360.0 if l <= -180.0 else l


def parse_midas(text: str, frame: str) -> GnssVelocityField:
    """Parse MIDAS velocity-file text for a declared reference frame.

    ``frame`` must be a known code; it is the caller's responsibility to pass
    the frame that matches the file (NGL encodes it in the filename, e.g.
    ``midas.IGS14.txt``), and we record it so no later step can mix frames.
    """
    if frame not in KNOWN_FRAMES:
        raise ValueError(f"unknown reference frame '{frame}'; known: {sorted(KNOWN_FRAMES)}")
    stations: list[GnssStation] = []
    for line in text.splitlines():
        parts = line.split()
        if len(parts) < 27:
            continue
        try:
            sid = parts[0]
            first = float(parts[2])
            last = float(parts[3])
            dur = float(parts[4])
            ve, vn, vu = float(parts[8]), float(parts[9]), float(parts[10])
            sve, svn, svu = float(parts[11]), float(parts[12]), float(parts[13])
            lat = float(parts[24])
            lon = normalize_lon(float(parts[25]))
            height = float(parts[26])
        except (ValueError, IndexError):
            continue
        stations.append(
            GnssStation(
                station_id=sid,
                lat=lat,
                lon=lon,
                height_m=height,
                ve_mm_yr=ve * M_TO_MM,
                vn_mm_yr=vn * M_TO_MM,
                vu_mm_yr=vu * M_TO_MM,
                sve_mm_yr=sve * M_TO_MM,
                svn_mm_yr=svn * M_TO_MM,
                svu_mm_yr=svu * M_TO_MM,
                first_epoch=first,
                last_epoch=last,
                duration_yr=dur,
            )
        )
    return GnssVelocityField(
        frame=frame,
        stations=stations,
        provenance={"n_parsed": len(stations), "frame_label": KNOWN_FRAMES[frame]},
    )


def merge_same_frame(fields: list[GnssVelocityField]) -> GnssVelocityField:
    """Merge velocity fields, refusing to mix reference frames (L12).

    This is the guard that keeps IGS14 and IGS20 (or a global and a plate-fixed
    frame) from being concatenated into a meaningless combined field.
    """
    if not fields:
        raise ValueError("no fields to merge")
    frame = fields[0].frame
    for f in fields:
        if f.frame != frame:
            raise ValueError(
                f"refusing to merge reference frames '{frame}' and '{f.frame}': "
                "velocities in different frames are not comparable"
            )
    merged = [s for f in fields for s in f.stations]
    return GnssVelocityField(frame=frame, stations=merged, provenance={"n_merged": len(merged)})
