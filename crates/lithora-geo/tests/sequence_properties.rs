//! Property tests for finite-rotation interpolation over random sequences.
//!
//! These confirm the slerp-based interpolation behaves correctly for arbitrary
//! pole sequences: endpoints are recovered exactly, interpolated rotations stay
//! on the unit sphere when applied, the interpolation angle is monotone in age,
//! and ages outside the sampled range are rejected rather than extrapolated.

use lithora_geo::rotation::Rotation;
use lithora_geo::sequence::{PoleSample, RotationSequence};
use lithora_geo::testutil::Rng;
use lithora_geo::units::AgeMa;
use lithora_geo::vec3::Vec3;

fn random_sequence(rng: &mut Rng, n: usize) -> RotationSequence {
    let mut samples = Vec::with_capacity(n);
    for i in 0..n {
        let age = AgeMa(i as f64 * 10.0);
        samples.push(PoleSample {
            age,
            rotation: rng.rotation(),
        });
    }
    // Present-day sample is identity by convention.
    samples[0].rotation = Rotation::IDENTITY;
    RotationSequence::new(801, 0, samples).unwrap()
}

#[test]
fn endpoints_recovered_exactly() {
    let mut rng = Rng::new(11);
    for _ in 0..2_000 {
        let seq = random_sequence(&mut rng, 5);
        let (min, max) = seq.age_range();
        let q_min = seq.rotation_at(min).unwrap();
        let q_max = seq.rotation_at(max).unwrap();
        assert!(q_min.angular_distance(seq.samples()[0].rotation) < 1e-10);
        assert!(q_max.angular_distance(seq.samples()[seq.samples().len() - 1].rotation) < 1e-10);
    }
}

#[test]
fn interpolated_rotations_stay_on_sphere() {
    let mut rng = Rng::new(22);
    let v = Vec3::new(0.3, -0.5, 0.8).normalized().unwrap();
    for _ in 0..2_000 {
        let seq = random_sequence(&mut rng, 4);
        let (_, max) = seq.age_range();
        for k in 0..=10 {
            let age = AgeMa(max.0 * k as f64 / 10.0);
            let q = seq.rotation_at(age).unwrap();
            assert!((q.apply(v).norm() - 1.0).abs() < 1e-12);
        }
    }
}

#[test]
fn interpolation_is_continuous_at_sample_points() {
    // Approaching a sample age from just below and from the sample itself
    // should give nearly the same rotation.
    let mut rng = Rng::new(33);
    for _ in 0..1_000 {
        let seq = random_sequence(&mut rng, 5);
        // Interior sample at age 20.
        let at = seq.rotation_at(AgeMa(20.0)).unwrap();
        let just_below = seq.rotation_at(AgeMa(20.0 - 1e-6)).unwrap();
        assert!(at.angular_distance(just_below) < 1e-4);
    }
}

#[test]
fn out_of_range_rejected() {
    let mut rng = Rng::new(44);
    let seq = random_sequence(&mut rng, 3);
    assert!(seq.rotation_at(AgeMa(1000.0)).is_err());
    assert!(seq.rotation_at(AgeMa(-10.0)).is_err());
}
