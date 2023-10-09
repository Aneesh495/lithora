//! Gate G02 (engine side): reconstructed point positions agree with an
//! independent analytic reference below the predeclared tolerance of 1e-7
//! radians for pure rigid point reconstruction.
//!
//! The quaternion engine in `lithora-geo` applies a rotation with the
//! matrix-free sandwich form. Here we build a completely independent reference
//! by constructing the 3x3 rotation matrix from the Euler axis and angle via
//! Rodrigues' formula and multiplying it by the point. If the two agree to
//! 1e-7 rad over 10,000+ random axis/angle/point combinations, the engine's
//! rigid reconstruction is validated against an independent implementation.
//!
//! This is the analytic-reference half of G02. The pyGPlates differential
//! check for real published models is separate and requires that external
//! dependency; it is tracked as pending in the specification.

use lithora_geo::rotation::Rotation;
use lithora_geo::testutil::Rng;
use lithora_geo::vec3::Vec3;

/// Independent rotation of a vector using an explicit Rodrigues rotation
/// matrix. This shares no code with the quaternion `apply` path.
fn rodrigues_apply(axis: Vec3, angle: f64, v: Vec3) -> Vec3 {
    let k = axis.normalized().expect("nonzero axis");
    let (s, c) = (angle.sin(), angle.cos());
    // R v = v cos + (k x v) sin + k (k . v)(1 - cos)
    let kxv = k.cross(v);
    let kdotv = k.dot(v);
    Vec3::new(
        v.x * c + kxv.x * s + k.x * kdotv * (1.0 - c),
        v.y * c + kxv.y * s + k.y * kdotv * (1.0 - c),
        v.z * c + kxv.z * s + k.z * kdotv * (1.0 - c),
    )
}

/// Angular difference between two unit vectors, in radians.
fn angular_diff(a: Vec3, b: Vec3) -> f64 {
    a.angle_to(b)
}

const TOL_RAD: f64 = 1e-7;
const N_CASES: usize = 20_000;

#[test]
fn quaternion_reconstruction_matches_rodrigues_reference() {
    let mut rng = Rng::new(424242);
    let mut worst = 0.0_f64;
    for i in 0..N_CASES {
        let axis = rng.unit_vec();
        let angle = rng.range(0.0, std::f64::consts::PI);
        let point = rng.unit_vec();

        let q = Rotation::from_axis_angle(axis, angle);
        let engine = q.apply(point);
        let reference = rodrigues_apply(axis, angle, point);

        let diff = angular_diff(engine, reference);
        worst = worst.max(diff);
        assert!(
            diff < TOL_RAD,
            "case {i}: angular diff {diff} exceeds {TOL_RAD} (axis {axis:?} angle {angle})"
        );
    }
    // The worst case across all trials should be comfortably within tolerance.
    assert!(worst < TOL_RAD, "worst diff {worst}");
}

#[test]
fn composed_reconstruction_matches_sequential_reference() {
    // Two successive rotations should match applying the Rodrigues reference
    // twice, confirming the engine's composition and application agree with an
    // independent path for the pure rigid case.
    let mut rng = Rng::new(99099);
    for i in 0..(N_CASES / 2) {
        let axis1 = rng.unit_vec();
        let angle1 = rng.range(0.0, std::f64::consts::PI);
        let axis2 = rng.unit_vec();
        let angle2 = rng.range(0.0, std::f64::consts::PI);
        let point = rng.unit_vec();

        let q1 = Rotation::from_axis_angle(axis1, angle1);
        let q2 = Rotation::from_axis_angle(axis2, angle2);
        let engine = q1.then(q2).apply(point);

        let ref1 = rodrigues_apply(axis1, angle1, point);
        let reference = rodrigues_apply(axis2, angle2, ref1);

        let diff = angular_diff(engine, reference);
        assert!(
            diff < TOL_RAD,
            "case {i}: composed diff {diff} exceeds {TOL_RAD}"
        );
    }
}
