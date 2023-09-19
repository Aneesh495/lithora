"""Acquisition entry points that download, cache, and record provenance.

These functions fetch real data from NGL and USGS, write the raw bytes into a
cache directory (never committed), and emit a JSON provenance manifest beside
the cache so a later run can audit exactly what was downloaded and when. They
are intentionally thin wrappers over the parsers so that the same parsing code
is exercised by both the offline tests and live acquisition.
"""

from __future__ import annotations

import hashlib
import json
import os
import time

from .http import open_url
from .ngl import GnssVelocityField, parse_midas
from .usgs import EarthquakeCatalog, fetch_catalog

NGL_MIDAS_URL = "https://geodesy.unr.edu/velocities/midas.{frame}.txt"


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def acquire_gnss(
    frame: str = "IGS14",
    cache_dir: str = "data/raw/gnss",
    timeout_s: float = 60.0,
) -> GnssVelocityField:
    """Download the NGL MIDAS velocity file for a frame, cache it, and parse.

    The reference frame is part of the cache filename and the provenance, so a
    cached IGS14 file can never be mistaken for another frame.
    """
    os.makedirs(cache_dir, exist_ok=True)
    url = NGL_MIDAS_URL.format(frame=frame)
    raw_path = os.path.join(cache_dir, f"midas.{frame}.txt")
    manifest_path = os.path.join(cache_dir, f"midas.{frame}.provenance.json")

    with open_url(url, timeout_s=timeout_s) as resp:
        if resp.status != 200:
            raise RuntimeError(f"NGL returned HTTP {resp.status} for {url}")
        data = resp.read()

    with open(raw_path, "wb") as fh:
        fh.write(data)

    text = data.decode("utf-8", errors="replace")
    field = parse_midas(text, frame=frame)
    manifest = {
        "source": field.source,
        "citation": field.citation,
        "url": url,
        "frame": frame,
        "fetched_unix": time.time(),
        "sha256": _sha256(data),
        "bytes": len(data),
        "n_stations": len(field),
    }
    with open(manifest_path, "w") as fh:
        json.dump(manifest, fh, indent=2)
    field.provenance.update(manifest)
    return field


def acquire_earthquakes(
    starttime: str,
    endtime: str,
    minmagnitude: float = 5.0,
    cache_dir: str = "data/raw/usgs",
    **bbox,
) -> EarthquakeCatalog:
    """Fetch and cache a USGS earthquake catalog with provenance."""
    os.makedirs(cache_dir, exist_ok=True)
    catalog = fetch_catalog(starttime, endtime, minmagnitude=minmagnitude, **bbox)
    stamp = f"{starttime}_{endtime}_m{minmagnitude}".replace(":", "-")
    manifest_path = os.path.join(cache_dir, f"usgs.{stamp}.provenance.json")
    manifest = {
        "source": catalog.source,
        "query": catalog.query,
        "fetched_unix": catalog.fetched_unix,
        "n_events": len(catalog),
        "completeness_note": catalog.completeness_note,
    }
    with open(manifest_path, "w") as fh:
        json.dump(manifest, fh, indent=2)
    return catalog
