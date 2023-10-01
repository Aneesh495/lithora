//! The WGS84 ellipsoid and the geodetic/geocentric latitude distinction.
//!
//! Reconstruction math runs on a sphere, but real GNSS stations are reported
//! in geodetic coordinates on the WGS84 ellipsoid, and surface velocities are
//! tangent to that ellipsoid. Confusing geodetic latitude (the angle of the
//! ellipsoidal surface normal) with geocentric latitude (the angle of the
//! radius vector) introduces errors up to ~0.19 degrees near 45 N, which at
//! plate-motion scales is not negligible. This module makes the conversion
//! explicit so callers choose deliberately.

use crate::units::Degrees;

/// WGS84 semi-major axis in metres.
pub const WGS84_A: f64 = 6_378_137.0;
/// WGS84 flattening.
pub const WGS84_F: f64 = 1.0 / 298.257_223_563;

/// WGS84 semi-minor axis in metres, `b = a (1 - f)`.
pub fn wgs84_b() -> f64 {
    WGS84_A * (1.0 - WGS84_F)
}

/// First eccentricity squared, `e^2 = 2f - f^2`.
pub fn wgs84_e2() -> f64 {
    2.0 * WGS84_F - WGS84_F * WGS84_F
}

/// Convert geodetic latitude to geocentric latitude (both in degrees).
///
/// The relation is `tan(geocentric) = (1 - e^2) tan(geodetic)`.
pub fn geodetic_to_geocentric_lat_deg(geodetic_deg: f64) -> f64 {
    let gd = Degrees(geodetic_deg).to_radians();
    let gc = ((1.0 - wgs84_e2()) * gd.tan()).atan();
    Degrees::from_radians(gc).0
}

/// Convert geocentric latitude to geodetic latitude (both in degrees).
pub fn geocentric_to_geodetic_lat_deg(geocentric_deg: f64) -> f64 {
    let gc = Degrees(geocentric_deg).to_radians();
    let gd = (gc.tan() / (1.0 - wgs84_e2())).atan();
    Degrees::from_radians(gd).0
}

/// Radius of curvature in the prime vertical at a geodetic latitude, in metres.
/// This scales a surface angular rate into a local linear velocity.
pub fn prime_vertical_radius_m(geodetic_lat_deg: f64) -> f64 {
    let phi = Degrees(geodetic_lat_deg).to_radians();
    let s = phi.sin();
    WGS84_A / (1.0 - wgs84_e2() * s * s).sqrt()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn poles_and_equator_are_fixed_points() {
        for lat in [-90.0, 0.0, 90.0] {
            let gc = geodetic_to_geocentric_lat_deg(lat);
            assert!((gc - lat).abs() < 1e-9, "lat {lat} -> {gc}");
        }
    }

    #[test]
    fn geodetic_geocentric_round_trip() {
        for lat in [12.3, 45.0, -67.8, 88.0] {
            let back = geocentric_to_geodetic_lat_deg(geodetic_to_geocentric_lat_deg(lat));
            assert!((back - lat).abs() < 1e-9, "lat {lat} -> {back}");
        }
    }

    #[test]
    fn geocentric_is_smaller_in_northern_midlatitudes() {
        // Geocentric latitude is pulled toward the equator relative to geodetic.
        let gd = 45.0;
        let gc = geodetic_to_geocentric_lat_deg(gd);
        assert!(
            gc < gd && gd - gc > 0.1 && gd - gc < 0.2,
            "diff {}",
            gd - gc
        );
    }

    #[test]
    fn prime_vertical_radius_is_near_semi_major_at_equator() {
        assert!((prime_vertical_radius_m(0.0) - WGS84_A).abs() < 1e-6);
        assert!(prime_vertical_radius_m(45.0) > WGS84_A);
    }
}
