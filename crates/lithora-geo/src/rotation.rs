//! Finite rotations on the sphere, represented as unit quaternions.
//!
//! A plate's motion between two geological times is a rigid rotation of the
//! sphere about an Euler pole through a finite angle. We represent it as a
//! unit quaternion because quaternion composition is numerically stable,
//! avoids gimbal lock, and makes the non-commutativity of successive
//! rotations explicit (plate circuits chain many of them).
//!
//! # Conventions
//!
//! - A quaternion `q = (w, x, y, z)` with `w = cos(theta/2)` and
//!   `(x,y,z) = sin(theta/2) * axis_hat` encodes an *active* right-handed
//!   rotation by `theta` about the unit `axis_hat`.
//! - Composition `a.then(b)` means: first apply `a`, then apply `b`. In
//!   quaternion terms the combined rotation is `b.q * a.q`. Getting this
//!   order backwards is the classic plate-circuit bug, so the method name
//!   encodes the temporal order rather than the raw multiplication order.
//! - `q` and `-q` represent the same rotation. We canonicalise to `w >= 0`
//!   so equality and logging are stable, but all math treats them as equal.

use crate::units::Degrees;
use crate::vec3::Vec3;
use serde::{Deserialize, Serialize};

/// A finite rotation as a unit quaternion `(w, x, y, z)`.
#[derive(Debug, Clone, Copy, PartialEq, Serialize, Deserialize)]
pub struct Rotation {
    pub w: f64,
    pub x: f64,
    pub y: f64,
    pub z: f64,
}

impl Rotation {
    /// The identity rotation (no motion).
    pub const IDENTITY: Rotation = Rotation {
        w: 1.0,
        x: 0.0,
        y: 0.0,
        z: 0.0,
    };

    /// Build a rotation from an Euler axis and an angle in radians.
    ///
    /// The axis need not be normalised; a zero-length axis yields the
    /// identity (the only sensible interpretation of "rotate about nothing").
    /// The half-angle formulation is exact at `angle = 0` and stable for the
    /// very small angles typical of short stage rotations.
    pub fn from_axis_angle(axis: Vec3, angle_rad: f64) -> Self {
        let axis_hat = match axis.normalized() {
            Some(a) => a,
            None => return Rotation::IDENTITY,
        };
        let half = 0.5 * angle_rad;
        let s = half.sin();
        Rotation {
            w: half.cos(),
            x: axis_hat.x * s,
            y: axis_hat.y * s,
            z: axis_hat.z * s,
        }
        .canonical()
    }

    /// Build from an Euler pole given as latitude/longitude on the sphere and
    /// an angle in degrees, the form rotation files use.
    pub fn from_euler_pole(pole: crate::coord::LatLon, angle_deg: f64) -> Self {
        Rotation::from_axis_angle(pole.to_unit_vec(), Degrees(angle_deg).to_radians())
    }

    /// Quaternion norm. Should stay very close to 1 for a valid rotation.
    pub fn norm(self) -> f64 {
        (self.w * self.w + self.x * self.x + self.y * self.y + self.z * self.z).sqrt()
    }

    /// Return a renormalised copy, guarding against drift after many
    /// compositions. Returns identity if the quaternion collapsed to zero,
    /// which should never happen for well-formed inputs.
    pub fn normalized(self) -> Rotation {
        let n = self.norm();
        if n < 1e-300 {
            return Rotation::IDENTITY;
        }
        let inv = 1.0 / n;
        Rotation {
            w: self.w * inv,
            x: self.x * inv,
            y: self.y * inv,
            z: self.z * inv,
        }
    }

    /// Canonical sign convention: force `w >= 0` so `q` and `-q` compare equal.
    pub fn canonical(self) -> Rotation {
        if self.w < 0.0 {
            Rotation {
                w: -self.w,
                x: -self.x,
                y: -self.y,
                z: -self.z,
            }
        } else {
            self
        }
    }

    /// The inverse rotation (conjugate, since the quaternion is unit length).
    pub fn inverse(self) -> Rotation {
        Rotation {
            w: self.w,
            x: -self.x,
            y: -self.y,
            z: -self.z,
        }
        .canonical()
    }

    /// Raw Hamilton product `self.q * rhs.q` (apply `rhs` first, then `self`).
    fn mul(self, rhs: Rotation) -> Rotation {
        Rotation {
            w: self.w * rhs.w - self.x * rhs.x - self.y * rhs.y - self.z * rhs.z,
            x: self.w * rhs.x + self.x * rhs.w + self.y * rhs.z - self.z * rhs.y,
            y: self.w * rhs.y - self.x * rhs.z + self.y * rhs.w + self.z * rhs.x,
            z: self.w * rhs.z + self.x * rhs.y - self.y * rhs.x + self.z * rhs.w,
        }
    }

    /// Compose two rotations in *temporal* order: the result applies `self`
    /// first and then `other`. This reads the way plate circuits are spoken
    /// about ("rotate A to B, then B to anchor") and hides the reversed
    /// multiplication order that trips people up.
    pub fn then(self, other: Rotation) -> Rotation {
        other.mul(self).normalized().canonical()
    }

    /// Apply this rotation to a vector (active rotation).
    ///
    /// Uses the `v' = v + 2 w (u x v) + 2 u x (u x v)` form with
    /// `u = (x,y,z)`, which avoids constructing a 3x3 matrix and is accurate
    /// for small angles.
    pub fn apply(self, v: Vec3) -> Vec3 {
        let u = Vec3::new(self.x, self.y, self.z);
        let t = u.cross(v).scale(2.0);
        v.add(t.scale(self.w)).add(u.cross(t))
    }

    /// Recover the rotation angle in radians, always in `[0, pi]`.
    pub fn angle_rad(self) -> f64 {
        let c = self.canonical();
        let sin_half = (c.x * c.x + c.y * c.y + c.z * c.z).sqrt();
        2.0 * sin_half.atan2(c.w)
    }

    /// Recover the Euler axis as a unit vector. Undefined for the identity,
    /// where we return `None` because any axis is equally valid.
    pub fn axis(self) -> Option<Vec3> {
        Vec3::new(self.x, self.y, self.z).normalized()
    }

    /// Angular distance to another rotation, in radians: the angle of the
    /// relative rotation `self^-1 then other`. Zero when they are equal
    /// (including the `q`/`-q` ambiguity).
    pub fn angular_distance(self, other: Rotation) -> f64 {
        self.inverse().then(other).angle_rad()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::coord::LatLon;
    use std::f64::consts::PI;

    fn vclose(a: Vec3, b: Vec3, tol: f64) -> bool {
        a.sub(b).norm() < tol
    }

    #[test]
    fn identity_does_nothing() {
        let v = Vec3::new(0.3, -0.7, 0.65);
        assert!(vclose(Rotation::IDENTITY.apply(v), v, 1e-15));
    }

    #[test]
    fn quarter_turn_about_z() {
        let r = Rotation::from_axis_angle(Vec3::new(0.0, 0.0, 1.0), PI / 2.0);
        let v = Vec3::new(1.0, 0.0, 0.0);
        assert!(vclose(r.apply(v), Vec3::new(0.0, 1.0, 0.0), 1e-14));
    }

    #[test]
    fn inverse_undoes_rotation() {
        let r = Rotation::from_euler_pole(LatLon::new(12.0, 34.0), 47.0);
        let v = Vec3::new(0.2, 0.9, -0.3).normalized().unwrap();
        let round = r.then(r.inverse()).apply(v);
        assert!(vclose(round, v, 1e-13));
    }

    #[test]
    fn composition_is_noncommutative() {
        let a = Rotation::from_axis_angle(Vec3::new(0.0, 0.0, 1.0), PI / 2.0);
        let b = Rotation::from_axis_angle(Vec3::new(0.0, 1.0, 0.0), PI / 2.0);
        let v = Vec3::new(1.0, 0.0, 0.0);
        let ab = a.then(b).apply(v);
        let ba = b.then(a).apply(v);
        assert!(
            !vclose(ab, ba, 1e-6),
            "rotations about different axes must not commute"
        );
    }

    #[test]
    fn temporal_order_matches_manual_apply() {
        // then() must equal applying a first, then b.
        let a = Rotation::from_euler_pole(LatLon::new(10.0, 20.0), 15.0);
        let b = Rotation::from_euler_pole(LatLon::new(-30.0, 100.0), 25.0);
        let v = Vec3::new(0.4, -0.5, 0.76).normalized().unwrap();
        let composed = a.then(b).apply(v);
        let stepwise = b.apply(a.apply(v));
        assert!(vclose(composed, stepwise, 1e-13));
    }

    #[test]
    fn small_angle_is_accurate() {
        // A 1e-7 radian rotation about z should move (1,0,0) by ~1e-7 in y.
        let r = Rotation::from_axis_angle(Vec3::new(0.0, 0.0, 1.0), 1e-7);
        let v = r.apply(Vec3::new(1.0, 0.0, 0.0));
        assert!((v.y - 1e-7).abs() < 1e-14);
    }

    #[test]
    fn near_antipodal_pi_rotation() {
        let r = Rotation::from_axis_angle(Vec3::new(0.0, 0.0, 1.0), PI);
        let v = r.apply(Vec3::new(1.0, 0.0, 0.0));
        assert!(vclose(v, Vec3::new(-1.0, 0.0, 0.0), 1e-14));
        assert!((r.angle_rad() - PI).abs() < 1e-12);
    }

    #[test]
    fn angle_and_axis_recovery() {
        let axis = Vec3::new(0.2, 0.5, -0.9).normalized().unwrap();
        let r = Rotation::from_axis_angle(axis, 1.1);
        assert!((r.angle_rad() - 1.1).abs() < 1e-12);
        let rec = r.axis().unwrap();
        // axis may come back flipped with angle; here angle < pi so same sign.
        assert!(vclose(rec, axis, 1e-12));
    }

    #[test]
    fn q_and_negq_equal() {
        let r = Rotation::from_euler_pole(LatLon::new(5.0, 5.0), 30.0);
        let neg = Rotation {
            w: -r.w,
            x: -r.x,
            y: -r.y,
            z: -r.z,
        };
        assert!(r.angular_distance(neg) < 1e-12);
    }

    #[test]
    fn zero_axis_is_identity() {
        let r = Rotation::from_axis_angle(Vec3::ZERO, 1.3);
        assert_eq!(r, Rotation::IDENTITY);
    }
}
