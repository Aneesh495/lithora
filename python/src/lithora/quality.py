"""Station quality flags (capability L10).

Not every station is equally trustworthy for a rigid fit. A short record, a
very high reported uncertainty, or a velocity far larger than plausible plate
motion are all reasons to down-weight or exclude a station, and the decision
should be explicit and auditable, not buried in a fitting routine. This module
computes per-station quality flags from the metadata the MIDAS product
provides, so the eligibility and weighting decisions are frozen and visible.

The flags are deliberately conservative and descriptive. They do not silently
drop stations; the caller decides what to do with a flagged station, and the
flag string travels with it for provenance.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class QualityReport:
    station_id: str
    duration_yr: float
    sigma_mm_yr: float
    speed_mm_yr: float
    flags: list[str]

    @property
    def eligible(self) -> bool:
        """Eligible for a rigid fit when no disqualifying flag is present."""
        disqualifying = {"short_record", "implausible_speed"}
        return not any(f in disqualifying for f in self.flags)


def flag_stations(
    station_ids: list[str],
    duration_yr: np.ndarray,
    sigma_mm_yr: np.ndarray,
    speed_mm_yr: np.ndarray,
    min_years: float = 5.0,
    max_speed_mm_yr: float = 200.0,
    high_sigma_mm_yr: float = 3.0,
) -> list[QualityReport]:
    """Compute quality flags per station from its metadata.

    - ``short_record``: fewer than ``min_years`` of observations.
    - ``implausible_speed``: speed above ``max_speed_mm_yr``, which no plate
      interior reaches and signals a data problem.
    - ``high_uncertainty``: reported sigma above ``high_sigma_mm_yr`` (a
      descriptive flag, not disqualifying on its own).
    """
    dur = np.asarray(duration_yr, float).reshape(-1)
    sig = np.asarray(sigma_mm_yr, float).reshape(-1)
    spd = np.asarray(speed_mm_yr, float).reshape(-1)
    out: list[QualityReport] = []
    for i, sid in enumerate(station_ids):
        flags: list[str] = []
        if dur[i] < min_years:
            flags.append("short_record")
        if spd[i] > max_speed_mm_yr:
            flags.append("implausible_speed")
        if sig[i] > high_sigma_mm_yr:
            flags.append("high_uncertainty")
        out.append(
            QualityReport(
                station_id=sid,
                duration_yr=float(dur[i]),
                sigma_mm_yr=float(sig[i]),
                speed_mm_yr=float(spd[i]),
                flags=flags,
            )
        )
    return out
