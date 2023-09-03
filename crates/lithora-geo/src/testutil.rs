//! Deterministic test utilities: a small seeded PRNG and random samplers.
//!
//! The large property campaigns (gate G01) need hundreds of thousands of
//! reproducible random cases without pulling in an external RNG crate. This
//! module provides a SplitMix64 generator, which is fast, has good
//! statistical quality for test sampling, and is fully reproducible from a
//! seed so any failing case can be replayed exactly.
//!
//! It is compiled only for tests and benches; it is not part of the shipped
//! numerical surface.

use crate::coord::LatLon;
use crate::rotation::Rotation;
use crate::vec3::Vec3;

/// A SplitMix64 pseudo-random generator. Reproducible and dependency free.
#[derive(Debug, Clone)]
pub struct Rng {
    state: u64,
}

impl Rng {
    pub fn new(seed: u64) -> Self {
        Rng { state: seed }
    }

    /// Next raw 64-bit value.
    pub fn next_u64(&mut self) -> u64 {
        self.state = self.state.wrapping_add(0x9E37_79B9_7F4A_7C15);
        let mut z = self.state;
        z = (z ^ (z >> 30)).wrapping_mul(0xBF58_476D_1CE4_E5B9);
        z = (z ^ (z >> 27)).wrapping_mul(0x94D0_49BB_1331_11EB);
        z ^ (z >> 31)
    }

    /// Uniform in `[0, 1)`.
    pub fn next_f64(&mut self) -> f64 {
        // 53-bit mantissa for a uniform double.
        (self.next_u64() >> 11) as f64 / (1u64 << 53) as f64
    }

    /// Uniform in `[lo, hi)`.
    pub fn range(&mut self, lo: f64, hi: f64) -> f64 {
        lo + (hi - lo) * self.next_f64()
    }

    /// A point uniformly distributed on the unit sphere (area measure), via
    /// the standard inverse-CDF method: longitude uniform, sine of latitude
    /// uniform.
    pub fn unit_sphere_point(&mut self) -> LatLon {
        let lon = self.range(-180.0, 180.0);
        let sin_lat = self.range(-1.0, 1.0);
        let lat = sin_lat.asin().to_degrees();
        LatLon::new(lat, lon)
    }

    /// A uniformly random rotation. The axis is a uniform sphere direction
    /// and the angle is uniform in `[0, pi]`, which is sufficient for the
    /// invariant and differential checks (every rotation is reachable since
    /// `q` and `-q` coincide).
    pub fn rotation(&mut self) -> Rotation {
        let axis_point = self.unit_sphere_point().to_unit_vec();
        let angle = self.range(0.0, std::f64::consts::PI);
        Rotation::from_axis_angle(axis_point, angle)
    }

    /// A random unit vector direction.
    pub fn unit_vec(&mut self) -> Vec3 {
        self.unit_sphere_point().to_unit_vec()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn rng_is_reproducible() {
        let mut a = Rng::new(42);
        let mut b = Rng::new(42);
        for _ in 0..1000 {
            assert_eq!(a.next_u64(), b.next_u64());
        }
    }

    #[test]
    fn uniform_in_unit_interval() {
        let mut r = Rng::new(7);
        let mut sum = 0.0;
        let n = 100_000;
        for _ in 0..n {
            let x = r.next_f64();
            assert!((0.0..1.0).contains(&x));
            sum += x;
        }
        let mean = sum / n as f64;
        assert!((mean - 0.5).abs() < 0.01, "mean {mean}");
    }

    #[test]
    fn sphere_points_are_unit_length() {
        let mut r = Rng::new(99);
        for _ in 0..1000 {
            let v = r.unit_sphere_point().to_unit_vec();
            assert!((v.norm() - 1.0).abs() < 1e-12);
        }
    }

    #[test]
    fn random_rotations_are_unit_quaternions() {
        let mut r = Rng::new(123);
        for _ in 0..1000 {
            let q = r.rotation();
            assert!((q.norm() - 1.0).abs() < 1e-9);
        }
    }
}
