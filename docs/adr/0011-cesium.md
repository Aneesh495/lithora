# 11. CesiumJS for the atlas

## Context

The atlas needs an accurate 3D globe with geographic positioning, camera
control, and picking, rendering thousands of station glyphs and vectors.

## Decision

Use CesiumJS with a Vite + TypeScript build.

## Alternatives

- deck.gl / Mapbox: strong 2D and 2.5D, but a true globe with ECEF geometry is
  more natural in Cesium for plate-scale work.
- Three.js from scratch: full control but we would reimplement globe geometry,
  imagery, and camera handling.

## Consequences

A real globe with ECEF math that matches the analysis-side conventions, and
built-in picking for the station inspector. Velocity arrows are placed with an
original east/north to ECEF helper so the visualisation stays geometrically
consistent with the Python and Rust math. The build produces a static site;
imagery tiles require network access at view time.
