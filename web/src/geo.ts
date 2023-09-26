// Original geometry helpers for placing tangent-plane velocity vectors on the
// globe. A GNSS velocity is an east/north vector in the local tangent plane;
// to draw it as an arrow in 3D we convert the station to ECEF, build the local
// east/north/up basis there, and offset the arrow tip along that basis scaled
// by the (exaggerated) velocity. This mirrors the Python `local_enu_basis` so
// the visualization is geometrically consistent with the analysis.

import { Cartesian3 } from "cesium";

const DEG = Math.PI / 180;
// Mean Earth radius in metres, matching the analysis side.
const R = 6_371_008.8;

export function latLonToEcef(latDeg: number, lonDeg: number, height = 0): Cartesian3 {
  const lat = latDeg * DEG;
  const lon = lonDeg * DEG;
  const r = R + height;
  return new Cartesian3(
    r * Math.cos(lat) * Math.cos(lon),
    r * Math.cos(lat) * Math.sin(lon),
    r * Math.sin(lat),
  );
}

// Local east and north unit vectors (ECEF) at a geographic point.
export function enuBasis(latDeg: number, lonDeg: number): { east: Cartesian3; north: Cartesian3 } {
  const lat = latDeg * DEG;
  const lon = lonDeg * DEG;
  const east = new Cartesian3(-Math.sin(lon), Math.cos(lon), 0);
  const north = new Cartesian3(
    -Math.sin(lat) * Math.cos(lon),
    -Math.sin(lat) * Math.sin(lon),
    Math.cos(lat),
  );
  return { east, north };
}

// Arrow tip position for a velocity (east, north) in mm/yr, exaggerated. The
// exaggeration turns mm/yr into a visible number of metres on the globe: at
// exaggeration E, one mm/yr maps to E * metresPerMmYr metres. Callers choose
// metresPerMmYr so a legend can state the mapping honestly.
export function arrowTip(
  latDeg: number,
  lonDeg: number,
  ve: number,
  vn: number,
  exaggeration: number,
  metresPerMmYr = 3000,
): Cartesian3 {
  const base = latLonToEcef(latDeg, lonDeg);
  const { east, north } = enuBasis(latDeg, lonDeg);
  const scale = exaggeration * metresPerMmYr;
  return new Cartesian3(
    base.x + (east.x * ve + north.x * vn) * scale,
    base.y + (east.y * ve + north.y * vn) * scale,
    base.z + (east.z * ve + north.z * vn) * scale,
  );
}

export function speed(ve: number, vn: number): number {
  return Math.hypot(ve, vn);
}
