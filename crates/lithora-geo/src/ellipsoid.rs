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

/// Geodesic distance in metres between two geodetic points on the WGS84
/// ellipsoid, by Vincenty's inverse formula.
///
/// This is the ellipsoidal counterpart to the spherical great-circle distance
/// in [`crate::polygon`]. It matters because the spherical approximation can
/// be off by up to about 0.5 percent for long paths, and plate-boundary
/// profiles span hundreds of kilometres. The function returns `None` for the
/// (near-)antipodal case where Vincenty's iteration does not converge, which
/// the caller should treat as "use a different method" rather than a silent
/// wrong number.
pub fn vincenty_distance_m(
    lat1_deg: f64,
    lon1_deg: f64,
    lat2_deg: f64,
    lon2_deg: f64,
) -> Option<f64> {
    let a = WGS84_A;
    let f = WGS84_F;
    let b = wgs84_b();
    let phi1 = Degrees(lat1_deg).to_radians();
    let phi2 = Degrees(lat2_deg).to_radians();
    let l = Degrees(lon2_deg - lon1_deg).to_radians();

    // Reduced latitudes.
    let u1 = ((1.0 - f) * phi1.tan()).atan();
    let u2 = ((1.0 - f) * phi2.tan()).atan();
    let (sin_u1, cos_u1) = (u1.sin(), u1.cos());
    let (sin_u2, cos_u2) = (u2.sin(), u2.cos());

    let mut lambda = l;

    for _ in 0..200 {
        let sin_lambda = lambda.sin();
        let cos_lambda = lambda.cos();
        let sin_sigma = ((cos_u2 * sin_lambda).powi(2)
            + (cos_u1 * sin_u2 - sin_u1 * cos_u2 * cos_lambda).powi(2))
        .sqrt();
        if sin_sigma == 0.0 {
            return Some(0.0); // coincident points
        }
        let cos_sigma = sin_u1 * sin_u2 + cos_u1 * cos_u2 * cos_lambda;
        let sigma = sin_sigma.atan2(cos_sigma);
        let sin_alpha = cos_u1 * cos_u2 * sin_lambda / sin_sigma;
        let cos_sq_alpha = 1.0 - sin_alpha * sin_alpha;
        let cos_2sigma_m = if cos_sq_alpha != 0.0 {
            cos_sigma - 2.0 * sin_u1 * sin_u2 / cos_sq_alpha
        } else {
            0.0 // equatorial line
        };
        let c = f / 16.0 * cos_sq_alpha * (4.0 + f * (4.0 - 3.0 * cos_sq_alpha));
        let lambda_prev = lambda;
        lambda = l
            + (1.0 - c)
                * f
                * sin_alpha
                * (sigma
                    + c * sin_sigma
                        * (cos_2sigma_m
                            + c * cos_sigma * (-1.0 + 2.0 * cos_2sigma_m * cos_2sigma_m)));
        if (lambda - lambda_prev).abs() < 1e-12 {
            let u_sq = cos_sq_alpha * (a * a - b * b) / (b * b);
            let big_a =
                1.0 + u_sq / 16384.0 * (4096.0 + u_sq * (-768.0 + u_sq * (320.0 - 175.0 * u_sq)));
            let big_b = u_sq / 1024.0 * (256.0 + u_sq * (-128.0 + u_sq * (74.0 - 47.0 * u_sq)));
            let delta_sigma = big_b
                * sin_sigma
                * (cos_2sigma_m
                    + big_b / 4.0
                        * (cos_sigma * (-1.0 + 2.0 * cos_2sigma_m * cos_2sigma_m)
                            - big_b / 6.0
                                * cos_2sigma_m
                                * (-3.0 + 4.0 * sin_sigma * sin_sigma)
                                * (-3.0 + 4.0 * cos_2sigma_m * cos_2sigma_m)));
            return Some(b * big_a * (sigma - delta_sigma));
        }
    }
    None // failed to converge (near-antipodal)
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

    #[test]
    fn vincenty_coincident_is_zero() {
        assert_eq!(vincenty_distance_m(40.0, -75.0, 40.0, -75.0), Some(0.0));
    }

    #[test]
    fn vincenty_one_degree_of_latitude() {
        // One degree of latitude is about 110.6 km on the WGS84 ellipsoid.
        let d = vincenty_distance_m(40.0, 0.0, 41.0, 0.0).unwrap();
        assert!((d - 111_034.0).abs() < 200.0, "d = {d}");
    }

    #[test]
    fn vincenty_matches_known_long_path() {
        // Approximate distance from near-equator to a mid-latitude point.
        // Flinders Peak to Buninyong (Vincenty's own test pair) is
        // about 54,972.271 m.
        let d = vincenty_distance_m(-37.95103, 144.42487, -37.65282, 143.92649).unwrap();
        assert!((d - 54_972.271).abs() < 1.0, "d = {d}");
    }

    #[test]
    fn vincenty_differs_from_spherical_on_long_paths() {
        use crate::coord::LatLon;
        use crate::polygon::great_circle_distance_m;
        use crate::units::EARTH_RADIUS_M;
        let a = LatLon::new(0.0, 0.0);
        let b = LatLon::new(60.0, 60.0);
        let vin = vincenty_distance_m(0.0, 0.0, 60.0, 60.0).unwrap();
        let sph = great_circle_distance_m(a, b, EARTH_RADIUS_M);
        // They agree to within a fraction of a percent but are not identical.
        let rel = (vin - sph).abs() / vin;
        assert!(rel < 0.01 && rel > 1e-5, "relative diff {rel}");
    }
}
