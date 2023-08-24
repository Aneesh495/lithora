//! Geographic coordinates and their mapping to the unit sphere.
//!
//! Plate reconstruction is a problem on the sphere: a finite rotation moves a
//! point to another point at the same radius. We therefore carry locations as
//! geographic (latitude, longitude) pairs and convert to unit Cartesian
//! vectors for rotation math. This module is explicitly about the *spherical*
//! model. Where an ellipsoidal distinction matters (geodetic vs geocentric
//! latitude, surface velocities in mm/yr), see [`crate::ellipsoid`].
//!
//! Convention: latitude in `[-90, 90]` degrees, positive north. Longitude in
//! `(-180, 180]` degrees, positive east. The unit-vector mapping is
//! `x = cos(lat) cos(lon)`, `y = cos(lat) sin(lon)`, `z = sin(lat)`, so the
//! +x axis pierces (0 N, 0 E), +y pierces (0 N, 90 E), and +z is the north
//! pole. This is a *geocentric* spherical latitude; it is not the geodetic
//! latitude of the WGS84 ellipsoid, and callers reconstructing real stations
//! must decide which they need (see the ellipsoid module).

use crate::units::Degrees;
use crate::vec3::Vec3;
use serde::{Deserialize, Serialize};

/// A location on the sphere in geographic coordinates (degrees).
#[derive(Debug, Clone, Copy, PartialEq, Serialize, Deserialize)]
pub struct LatLon {
    /// Latitude in degrees, positive north, in `[-90, 90]`.
    pub lat_deg: f64,
    /// Longitude in degrees, positive east.
    pub lon_deg: f64,
}

impl LatLon {
    pub fn new(lat_deg: f64, lon_deg: f64) -> Self {
        LatLon { lat_deg, lon_deg }
    }

    /// Map to a unit vector on the sphere (geocentric spherical convention).
    pub fn to_unit_vec(self) -> Vec3 {
        let lat = Degrees(self.lat_deg).to_radians();
        let lon = Degrees(self.lon_deg).to_radians();
        let (clat, slat) = (lat.cos(), lat.sin());
        let (clon, slon) = (lon.cos(), lon.sin());
        Vec3::new(clat * clon, clat * slon, slat)
    }

    /// Recover geographic coordinates from a (not necessarily unit) vector.
    /// Longitude is normalised to `(-180, 180]`. At the poles longitude is
    /// not defined; we return 0 there, which callers should treat as a flag
    /// rather than a meaningful bearing.
    pub fn from_vec(v: Vec3) -> Self {
        let r_xy = (v.x * v.x + v.y * v.y).sqrt();
        let lat = v.z.atan2(r_xy);
        let lon = if r_xy < 1e-15 { 0.0 } else { v.y.atan2(v.x) };
        LatLon {
            lat_deg: Degrees::from_radians(lat).0,
            lon_deg: normalize_lon_deg(Degrees::from_radians(lon).0),
        }
    }
}

/// Normalise a longitude in degrees to the half-open interval `(-180, 180]`.
pub fn normalize_lon_deg(lon: f64) -> f64 {
    let mut l = (lon + 180.0).rem_euclid(360.0) - 180.0;
    // rem_euclid maps 180 to -180; prefer the +180 representation so a point
    // exactly on the antimeridian is reported consistently.
    if l <= -180.0 {
        l += 360.0;
    }
    l
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn axes_map_to_expected_points() {
        let x = LatLon::new(0.0, 0.0).to_unit_vec();
        assert!((x.x - 1.0).abs() < 1e-15 && x.y.abs() < 1e-15 && x.z.abs() < 1e-15);
        let y = LatLon::new(0.0, 90.0).to_unit_vec();
        assert!(y.x.abs() < 1e-15 && (y.y - 1.0).abs() < 1e-15);
        let np = LatLon::new(90.0, 0.0).to_unit_vec();
        assert!((np.z - 1.0).abs() < 1e-15);
    }

    #[test]
    fn round_trip_generic_point() {
        let p = LatLon::new(37.5, -122.3);
        let back = LatLon::from_vec(p.to_unit_vec());
        assert!((p.lat_deg - back.lat_deg).abs() < 1e-9);
        assert!((p.lon_deg - back.lon_deg).abs() < 1e-9);
    }

    #[test]
    fn longitude_normalization() {
        assert!((normalize_lon_deg(190.0) - (-170.0)).abs() < 1e-12);
        assert!((normalize_lon_deg(-190.0) - 170.0).abs() < 1e-12);
        assert!((normalize_lon_deg(180.0) - 180.0).abs() < 1e-12);
        assert!((normalize_lon_deg(-180.0) - 180.0).abs() < 1e-12);
        assert!((normalize_lon_deg(540.0) - 180.0).abs() < 1e-12);
    }

    #[test]
    fn pole_has_unit_z() {
        let v = Vec3::new(0.0, 0.0, 1.0);
        let ll = LatLon::from_vec(v);
        assert!((ll.lat_deg - 90.0).abs() < 1e-9);
    }
}
