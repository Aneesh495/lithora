# Data card: USGS earthquake catalog

## Source

United States Geological Survey (USGS) FDSN event web service,
`https://earthquake.usgs.gov/fdsnws/event/1/`. Public API, no authentication.

## What it is

Earthquake events as GeoJSON features: longitude, latitude, depth (km),
magnitude, magnitude type, origin time, and an event id, filterable by time,
magnitude, and bounding box. Lithora keeps depth, magnitude type, time, and id
on every event.

## Role in Lithora

Context for active plate boundaries only. Earthquakes are never used to predict
dates or magnitudes, and visual proximity between an event and a velocity
anomaly is not treated as evidence of a mechanism. The atlas layer shows a
completeness caveat alongside the events.

## Completeness caveat

A fixed minimum-magnitude query is complete only above the regional magnitude
of completeness, which varies with network density and epoch. Event counts
below that threshold are not comparable across regions or time and must not be
read as changes in seismicity. This caveat travels with the exported layer.

## Acquired snapshots

The atlas layers were exported for 2014-01-01 to 2024-01-01, M >= 4.0:
California (432 events) and North America interior (113 events). The query and
counts are recorded in the provenance manifest under `data/raw/usgs`.

## Redistribution

Raw catalog responses are cached and gitignored; small exported layers for the
atlas are committed under `web/public/data`. Re-fetch with
`lithora.export_quakes`.
