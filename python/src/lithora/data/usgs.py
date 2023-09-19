"""USGS earthquake catalog acquisition (capability L10, context for L24).

Fetches events from the USGS FDSN event web service and records their full
provenance. Earthquakes in Lithora are strictly context for active plate
boundaries. We keep depth, magnitude type, catalog time window, and the event
id so that a map overlay can never silently imply a mechanism from mere visual
proximity, and we attach an explicit completeness caveat: a fixed-magnitude
threshold query is complete only above the network's magnitude of completeness,
which varies by region and era.

The client uses only the public API and the Python standard library, so it has
no third-party HTTP dependency. Network access is required at call time; the
parser is tested offline against a captured sample.
"""

from __future__ import annotations

import json
import time
import urllib.parse
from dataclasses import dataclass, field

from .http import open_url

FDSN_URL = "https://earthquake.usgs.gov/fdsnws/event/1/query"


@dataclass
class EarthquakeEvent:
    event_id: str
    time_ms: int
    lat: float
    lon: float
    depth_km: float
    mag: float
    mag_type: str
    place: str


@dataclass
class EarthquakeCatalog:
    events: list[EarthquakeEvent]
    query: dict
    fetched_unix: float
    source: str = "USGS FDSN event web service"
    completeness_note: str = (
        "A fixed minimum-magnitude query is complete only above the regional "
        "magnitude of completeness, which varies with network density and "
        "epoch. Counts below that threshold are not comparable across regions "
        "or time and must not be read as changes in seismicity."
    )
    provenance: dict = field(default_factory=dict)

    def __len__(self) -> int:
        return len(self.events)


def parse_geojson(text: str) -> list[EarthquakeEvent]:
    """Parse a USGS GeoJSON FeatureCollection into events.

    Missing or null numeric fields are skipped rather than coerced to zero,
    because a null magnitude is not a magnitude of zero.
    """
    doc = json.loads(text)
    out: list[EarthquakeEvent] = []
    for feat in doc.get("features", []):
        props = feat.get("properties", {})
        geom = feat.get("geometry") or {}
        coords = geom.get("coordinates")
        if not coords or len(coords) < 3:
            continue
        mag = props.get("mag")
        if mag is None:
            continue
        out.append(
            EarthquakeEvent(
                event_id=str(feat.get("id", "")),
                time_ms=int(props.get("time", 0)),
                lon=float(coords[0]),
                lat=float(coords[1]),
                depth_km=float(coords[2]),
                mag=float(mag),
                mag_type=str(props.get("magType", "unknown")),
                place=str(props.get("place", "")),
            )
        )
    return out


def fetch_catalog(
    starttime: str,
    endtime: str,
    minmagnitude: float = 5.0,
    minlatitude: float | None = None,
    maxlatitude: float | None = None,
    minlongitude: float | None = None,
    maxlongitude: float | None = None,
    timeout_s: float = 30.0,
) -> EarthquakeCatalog:
    """Fetch an earthquake catalog from USGS with full provenance.

    Dates are ISO ``YYYY-MM-DD``. Raises on a non-200 response rather than
    returning an empty catalog, so a network failure is a visible failure.
    """
    params = {
        "format": "geojson",
        "starttime": starttime,
        "endtime": endtime,
        "minmagnitude": minmagnitude,
    }
    for key, val in [
        ("minlatitude", minlatitude),
        ("maxlatitude", maxlatitude),
        ("minlongitude", minlongitude),
        ("maxlongitude", maxlongitude),
    ]:
        if val is not None:
            params[key] = val

    url = FDSN_URL + "?" + urllib.parse.urlencode(params)
    with open_url(url, timeout_s=timeout_s) as resp:
        if resp.status != 200:
            raise RuntimeError(f"USGS FDSN returned HTTP {resp.status}")
        text = resp.read().decode("utf-8")

    events = parse_geojson(text)
    return EarthquakeCatalog(
        events=events,
        query=params,
        fetched_unix=time.time(),
        provenance={"url": url, "n_events": len(events)},
    )
