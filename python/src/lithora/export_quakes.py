"""Export a USGS earthquake context layer for the atlas.

Earthquakes in Lithora are context for active boundaries, never a mechanism
claim. The exported layer keeps each event's depth, magnitude, magnitude type,
time, and id, and carries the catalog window and the completeness caveat so the
globe can show the caveat alongside the dots. Visual proximity to a velocity
anomaly proves nothing on its own, and the layer is labelled that way.
"""

from __future__ import annotations

import json
import os

from .data.usgs import fetch_catalog

# Region bounding boxes matching the velocity export regions.
REGION_BBOX = {
    "cal": (32.0, 42.0, -124.0, -114.0),
    "na": (32.0, 49.0, -104.0, -85.0),
    "jpn": (30.0, 46.0, 128.0, 146.0),
}


def export_quakes(
    region: str,
    starttime: str,
    endtime: str,
    out_path: str,
    minmagnitude: float = 4.0,
) -> dict:
    lo_lat, hi_lat, lo_lon, hi_lon = REGION_BBOX[region]
    catalog = fetch_catalog(
        starttime,
        endtime,
        minmagnitude=minmagnitude,
        minlatitude=lo_lat,
        maxlatitude=hi_lat,
        minlongitude=lo_lon,
        maxlongitude=hi_lon,
    )
    events = [
        {
            "id": e.event_id,
            "lat": e.lat,
            "lon": e.lon,
            "depth_km": e.depth_km,
            "mag": e.mag,
            "mag_type": e.mag_type,
            "time_ms": e.time_ms,
        }
        for e in catalog.events
    ]
    payload = {
        "region": region,
        "source": catalog.source,
        "window": {"start": starttime, "end": endtime},
        "min_magnitude": minmagnitude,
        "completeness_note": catalog.completeness_note,
        "n_events": len(events),
        "events": events,
    }
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, "w") as fh:
        json.dump(payload, fh)
    return {"out": out_path, "n": len(events), "region": region}


def main(argv=None):
    import argparse

    p = argparse.ArgumentParser(prog="lithora-export-quakes")
    p.add_argument("--region", default="cal")
    p.add_argument("--start", required=True)
    p.add_argument("--end", required=True)
    p.add_argument("--min-mag", type=float, default=4.0)
    p.add_argument("--out", required=True)
    args = p.parse_args(argv)
    print(json.dumps(export_quakes(args.region, args.start, args.end, args.out, args.min_mag), indent=2))


if __name__ == "__main__":
    main()
