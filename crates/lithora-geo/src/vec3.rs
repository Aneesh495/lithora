//! Minimal 3D vector used throughout the kinematic core.
//!
//! This is deliberately small and dependency free. It represents either a
//! point in Earth-centred Earth-fixed (ECEF) Cartesian coordinates or a
//! direction such as an Euler axis or an angular-velocity vector. The caller
//! owns the interpretation; the type only guarantees the arithmetic.

use serde::{Deserialize, Serialize};

/// A 3D Cartesian vector. Components are plain `f64`; the geometric meaning
/// (position vs direction, units) is documented by the caller.
#[derive(Debug, Clone, Copy, PartialEq, Serialize, Deserialize)]
pub struct Vec3 {
    pub x: f64,
    pub y: f64,
    pub z: f64,
}

impl Vec3 {
    pub const ZERO: Vec3 = Vec3 { x: 0.0, y: 0.0, z: 0.0 };

    #[inline]
    pub const fn new(x: f64, y: f64, z: f64) -> Self {
        Vec3 { x, y, z }
    }

    #[inline]
    pub fn dot(self, o: Vec3) -> f64 {
        self.x * o.x + self.y * o.y + self.z * o.z
    }

    /// Right-handed cross product `self x o`.
    #[inline]
    pub fn cross(self, o: Vec3) -> Vec3 {
        Vec3 {
            x: self.y * o.z - self.z * o.y,
            y: self.z * o.x - self.x * o.z,
            z: self.x * o.y - self.y * o.x,
        }
    }

    #[inline]
    pub fn norm_sq(self) -> f64 {
        self.dot(self)
    }

    #[inline]
    pub fn norm(self) -> f64 {
        self.norm_sq().sqrt()
    }

    #[inline]
    pub fn scale(self, s: f64) -> Vec3 {
        Vec3 { x: self.x * s, y: self.y * s, z: self.z * s }
    }

    #[inline]
    pub fn add(self, o: Vec3) -> Vec3 {
        Vec3 { x: self.x + o.x, y: self.y + o.y, z: self.z + o.z }
    }

    #[inline]
    pub fn sub(self, o: Vec3) -> Vec3 {
        Vec3 { x: self.x - o.x, y: self.y - o.y, z: self.z - o.z }
    }

    /// Return a unit vector in the same direction.
    ///
    /// Returns `None` when the vector is too close to zero to normalise
    /// reliably, which the caller must handle rather than producing NaNs.
    #[inline]
    pub fn normalized(self) -> Option<Vec3> {
        let n = self.norm();
        if n < 1e-300 {
            None
        } else {
            Some(self.scale(1.0 / n))
        }
    }

    /// Angle between two vectors in radians, computed with `atan2` of the
    /// cross-product magnitude over the dot product. This is numerically
    /// stable for both near-parallel and near-antiparallel inputs, unlike
    /// the naive `acos(dot/(|a||b|))` form which loses precision near 0 and
    /// pi and can produce NaN from rounding past +/-1.
    pub fn angle_to(self, o: Vec3) -> f64 {
        let cross_mag = self.cross(o).norm();
        let dot = self.dot(o);
        cross_mag.atan2(dot)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn cross_is_right_handed() {
        let x = Vec3::new(1.0, 0.0, 0.0);
        let y = Vec3::new(0.0, 1.0, 0.0);
        let z = x.cross(y);
        assert!((z.x).abs() < 1e-15 && (z.y).abs() < 1e-15 && (z.z - 1.0).abs() < 1e-15);
    }

    #[test]
    fn cross_is_anticommutative() {
        let a = Vec3::new(1.0, 2.0, 3.0);
        let b = Vec3::new(-2.0, 0.5, 4.0);
        let ab = a.cross(b);
        let ba = b.cross(a);
        assert!((ab.add(ba)).norm() < 1e-14);
    }

    #[test]
    fn angle_stable_near_zero_and_pi() {
        let a = Vec3::new(1.0, 0.0, 0.0);
        let almost = Vec3::new(1.0, 1e-9, 0.0);
        assert!(a.angle_to(almost) < 1e-8);
        let anti = Vec3::new(-1.0, 1e-9, 0.0);
        assert!((a.angle_to(anti) - std::f64::consts::PI).abs() < 1e-8);
    }

    #[test]
    fn zero_vector_has_no_direction() {
        assert!(Vec3::ZERO.normalized().is_none());
    }
}
