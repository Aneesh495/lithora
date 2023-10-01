//! Piecewise finite-rotation interpolation over geological time.
//!
//! A rotation model gives, for a moving plate relative to a fixed plate, a
//! list of *total reconstruction poles*: each is the finite rotation that
//! carries the plate from its present position to its position at a sampled
//! age. To reconstruct at an age between two samples we must interpolate the
//! rotation, not the reconstructed point.
//!
//! The distinction matters. Linearly interpolating the Cartesian position
//! between two reconstructed points cuts a chord through the sphere: the
//! intermediate point leaves the surface and the implied path is wrong. The
//! correct operation is spherical linear interpolation (slerp) of the
//! quaternion between the bracketing samples, which traces the minimal
//! rotation consistent with the two endpoints. This is the convention
//! GPlates and the rotation-file format assume, and we implement it directly.

use crate::error::{GeoError, Result};
use crate::rotation::Rotation;
use crate::units::AgeMa;

/// One sampled total reconstruction pole: the finite rotation at `age`.
#[derive(Debug, Clone, Copy)]
pub struct PoleSample {
    pub age: AgeMa,
    pub rotation: Rotation,
}

/// A time-ordered sequence of total reconstruction poles for one
/// moving/fixed plate pair. Samples are kept sorted by increasing age.
#[derive(Debug, Clone)]
pub struct RotationSequence {
    pub moving_plate: i64,
    pub fixed_plate: i64,
    samples: Vec<PoleSample>,
}

impl RotationSequence {
    /// Build from samples, sorting by age and validating non-emptiness.
    pub fn new(moving_plate: i64, fixed_plate: i64, mut samples: Vec<PoleSample>) -> Result<Self> {
        if samples.is_empty() {
            return Err(GeoError::EmptySequence(moving_plate));
        }
        samples.sort_by(|a, b| a.age.0.partial_cmp(&b.age.0).unwrap());
        Ok(RotationSequence {
            moving_plate,
            fixed_plate,
            samples,
        })
    }

    /// Youngest and oldest ages covered, in Ma.
    pub fn age_range(&self) -> (AgeMa, AgeMa) {
        (
            self.samples[0].age,
            self.samples[self.samples.len() - 1].age,
        )
    }

    pub fn samples(&self) -> &[PoleSample] {
        &self.samples
    }

    /// Total reconstruction rotation at an arbitrary age by slerp between the
    /// bracketing samples. Ages outside the sampled range are rejected rather
    /// than extrapolated: a model says nothing about times it does not cover.
    pub fn rotation_at(&self, age: AgeMa) -> Result<Rotation> {
        let (min, max) = self.age_range();
        if age.0 < min.0 - 1e-9 || age.0 > max.0 + 1e-9 {
            return Err(GeoError::AgeOutOfRange {
                age: age.0,
                min: min.0,
                max: max.0,
            });
        }
        // Exact-sample fast path and bracket search.
        for w in self.samples.windows(2) {
            let (a, b) = (w[0], w[1]);
            if age.0 >= a.age.0 - 1e-9 && age.0 <= b.age.0 + 1e-9 {
                let span = b.age.0 - a.age.0;
                let t = if span.abs() < 1e-12 {
                    0.0
                } else {
                    (age.0 - a.age.0) / span
                };
                return Ok(slerp(a.rotation, b.rotation, t));
            }
        }
        // Single-sample sequence that matched the range check.
        if self.samples.len() == 1 {
            return Ok(self.samples[0].rotation);
        }
        Err(GeoError::NoBracket(age.0))
    }
}

/// Spherical linear interpolation between two rotations.
///
/// `t = 0` returns `a`, `t = 1` returns `b`. We interpolate along the
/// shortest arc by flipping `b`'s sign when the quaternions point into
/// opposite hemispheres (recall `q` and `-q` are the same rotation). For
/// nearly identical rotations we fall back to normalised linear
/// interpolation to avoid dividing by a vanishing `sin`.
pub fn slerp(a: Rotation, b: Rotation, t: f64) -> Rotation {
    let a = a.normalized();
    let mut b = b.normalized();
    let mut dot = a.w * b.w + a.x * b.x + a.y * b.y + a.z * b.z;
    if dot < 0.0 {
        b = Rotation {
            w: -b.w,
            x: -b.x,
            y: -b.y,
            z: -b.z,
        };
        dot = -dot;
    }
    if dot > 0.999_999 {
        // Nearly parallel: linear blend then renormalise.
        let r = Rotation {
            w: a.w + t * (b.w - a.w),
            x: a.x + t * (b.x - a.x),
            y: a.y + t * (b.y - a.y),
            z: a.z + t * (b.z - a.z),
        };
        return r.normalized().canonical();
    }
    let theta0 = dot.acos();
    let sin0 = theta0.sin();
    let s0 = ((1.0 - t) * theta0).sin() / sin0;
    let s1 = (t * theta0).sin() / sin0;
    Rotation {
        w: s0 * a.w + s1 * b.w,
        x: s0 * a.x + s1 * b.x,
        y: s0 * a.y + s1 * b.y,
        z: s0 * a.z + s1 * b.z,
    }
    .normalized()
    .canonical()
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::coord::LatLon;
    use crate::vec3::Vec3;
    use std::f64::consts::PI;

    fn seq() -> RotationSequence {
        let s = vec![
            PoleSample {
                age: AgeMa(0.0),
                rotation: Rotation::IDENTITY,
            },
            PoleSample {
                age: AgeMa(10.0),
                rotation: Rotation::from_axis_angle(Vec3::new(0.0, 0.0, 1.0), PI / 2.0),
            },
        ];
        RotationSequence::new(802, 0, s).unwrap()
    }

    #[test]
    fn endpoints_recovered_exactly() {
        let q0 = seq().rotation_at(AgeMa(0.0)).unwrap();
        assert!(q0.angular_distance(Rotation::IDENTITY) < 1e-12);
        let q10 = seq().rotation_at(AgeMa(10.0)).unwrap();
        let expect = Rotation::from_axis_angle(Vec3::new(0.0, 0.0, 1.0), PI / 2.0);
        assert!(q10.angular_distance(expect) < 1e-12);
    }

    #[test]
    fn midpoint_is_half_the_angle_not_a_chord() {
        // Slerp of a 90-degree z-rotation at t=0.5 is a 45-degree z-rotation.
        let mid = seq().rotation_at(AgeMa(5.0)).unwrap();
        assert!((mid.angle_rad() - PI / 4.0).abs() < 1e-12);
        // And the reconstructed point stays on the unit sphere.
        let v = mid.apply(Vec3::new(1.0, 0.0, 0.0));
        assert!((v.norm() - 1.0).abs() < 1e-12);
        // A naive chord midpoint of (1,0,0) and (0,1,0) would have norm < 1.
        let chord = Vec3::new(0.5, 0.5, 0.0);
        assert!(chord.norm() < 0.999);
    }

    #[test]
    fn out_of_range_age_is_rejected() {
        assert!(matches!(
            seq().rotation_at(AgeMa(20.0)),
            Err(GeoError::AgeOutOfRange { .. })
        ));
    }

    #[test]
    fn slerp_endpoints() {
        let a = Rotation::from_euler_pole(LatLon::new(10.0, 20.0), 5.0);
        let b = Rotation::from_euler_pole(LatLon::new(-40.0, 120.0), 30.0);
        assert!(slerp(a, b, 0.0).angular_distance(a) < 1e-12);
        assert!(slerp(a, b, 1.0).angular_distance(b) < 1e-12);
    }
}
