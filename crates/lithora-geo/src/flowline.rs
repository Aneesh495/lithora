//! Small circles and flowlines about an Euler pole.
//!
//! When a plate rotates about an Euler pole, a point on it traces a small
//! circle centred on the pole: every point stays at a constant angular
//! distance (its colatitude) from the pole. This module computes those small
//! circles and the flowlines they imply, which are the natural way to draw a
//! plate's motion as a smooth arc rather than a series of discrete
//! reconstructed dots.
//!
//! A flowline here is the locus of a single point under a continuous rotation
//! about a fixed pole, sampled at a chosen angular step. It is exact (each
//! sample is a true rotation of the point), so it never leaves the sphere, and
//! it makes the geometric meaning of an Euler rotation visible: motion is
//! always perpendicular to the great circle from the pole to the point.

use crate::coord::LatLon;
use crate::rotation::Rotation;
use crate::vec3::Vec3;

/// The colatitude (angular distance in radians) of a point from an Euler pole.
/// This is the radius of the small circle the point travels on.
pub fn colatitude(pole: LatLon, point: LatLon) -> f64 {
    pole.to_unit_vec().angle_to(point.to_unit_vec())
}

/// Sample a flowline: the positions of `point` as it is rotated about `pole`
/// through a total angle, in `steps` equal increments. The returned vector
/// includes the starting point and `steps` further samples. The motion stays
/// exactly on the small circle of constant colatitude.
pub fn flowline(pole: LatLon, point: LatLon, total_angle_rad: f64, steps: usize) -> Vec<LatLon> {
    let axis = pole.to_unit_vec();
    let p = point.to_unit_vec();
    let n = steps.max(1);
    let mut out = Vec::with_capacity(n + 1);
    for i in 0..=n {
        let frac = i as f64 / n as f64;
        let r = Rotation::from_axis_angle(axis, total_angle_rad * frac);
        out.push(LatLon::from_vec(r.apply(p)));
    }
    out
}

/// The instantaneous motion direction (a unit tangent vector) of a point under
/// rotation about a pole. It is perpendicular to both the pole axis and the
/// position, i.e. along `axis x point`. Returns `None` at the pole itself,
/// where motion vanishes.
pub fn motion_direction(pole: LatLon, point: LatLon) -> Option<Vec3> {
    let axis = pole.to_unit_vec();
    let p = point.to_unit_vec();
    axis.cross(p).normalized()
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::f64::consts::PI;

    #[test]
    fn colatitude_of_equatorial_point_about_north_pole() {
        let pole = LatLon::new(90.0, 0.0);
        let point = LatLon::new(0.0, 0.0);
        assert!((colatitude(pole, point) - PI / 2.0).abs() < 1e-12);
    }

    #[test]
    fn flowline_stays_on_constant_colatitude() {
        let pole = LatLon::new(90.0, 0.0);
        let point = LatLon::new(30.0, 0.0);
        let c0 = colatitude(pole, point);
        let line = flowline(pole, point, PI, 20);
        assert_eq!(line.len(), 21);
        for pt in &line {
            let c = colatitude(pole, *pt);
            assert!((c - c0).abs() < 1e-12, "colatitude drifted: {c} vs {c0}");
            assert!((pt.to_unit_vec().norm() - 1.0).abs() < 1e-12);
        }
    }

    #[test]
    fn flowline_about_north_pole_is_constant_latitude() {
        // Rotating about the north pole moves longitude but keeps latitude.
        let pole = LatLon::new(90.0, 0.0);
        let point = LatLon::new(40.0, 10.0);
        let line = flowline(pole, point, PI / 2.0, 10);
        for pt in &line {
            assert!(
                (pt.lat_deg - 40.0).abs() < 1e-9,
                "latitude changed: {}",
                pt.lat_deg
            );
        }
    }

    #[test]
    fn motion_direction_is_tangent_and_perpendicular_to_pole_arc() {
        let pole = LatLon::new(90.0, 0.0);
        let point = LatLon::new(0.0, 0.0);
        let dir = motion_direction(pole, point).unwrap();
        let p = point.to_unit_vec();
        // Tangent to the sphere.
        assert!(dir.dot(p).abs() < 1e-12);
        // Perpendicular to the great circle from pole to point (which lies in
        // the plane of pole and point); for pole=+z, point=+x, motion is +y.
        assert!((dir.y - 1.0).abs() < 1e-12);
    }

    #[test]
    fn motion_vanishes_at_the_pole() {
        let pole = LatLon::new(90.0, 0.0);
        assert!(motion_direction(pole, LatLon::new(90.0, 0.0)).is_none());
    }
}
