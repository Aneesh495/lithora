//! Property tests for plate-circuit algebra over random rotations.
//!
//! These check the invariants a circuit must satisfy for arbitrary poles:
//! re-anchoring is consistent, composition up a chain equals the manual
//! product, and the identity relationships hold. They complement the targeted
//! unit tests in `circuit.rs` with random coverage.

use lithora_geo::circuit::PlateCircuit;
use lithora_geo::rotation::Rotation;
use lithora_geo::sequence::{PoleSample, RotationSequence};
use lithora_geo::testutil::Rng;
use lithora_geo::units::AgeMa;

fn const_link(moving: i64, fixed: i64, r: Rotation) -> RotationSequence {
    RotationSequence::new(
        moving,
        fixed,
        vec![
            PoleSample {
                age: AgeMa(0.0),
                rotation: Rotation::IDENTITY,
            },
            PoleSample {
                age: AgeMa(100.0),
                rotation: r,
            },
        ],
    )
    .unwrap()
}

#[test]
fn reanchoring_is_consistent_over_random_chains() {
    let mut rng = Rng::new(0xC0FFEE);
    for _ in 0..5_000 {
        // Random three-plate chain 3 -> 2 -> 1 -> 0.
        let r32 = rng.rotation();
        let r21 = rng.rotation();
        let r10 = rng.rotation();
        let mut c = PlateCircuit::new();
        c.add_link(const_link(3, 2, r32));
        c.add_link(const_link(2, 1, r21));
        c.add_link(const_link(1, 0, r10));

        let t = AgeMa(100.0);
        let to0 = c.total_rotation(3, 0, t).unwrap();
        let to1 = c.total_rotation(3, 1, t).unwrap();
        let one_to_zero = c.total_rotation(1, 0, t).unwrap();
        // total(3->0) == total(3->1) then total(1->0)
        assert!(to0.angular_distance(to1.then(one_to_zero)) < 1e-10);
    }
}

#[test]
fn chain_equals_manual_product() {
    let mut rng = Rng::new(0xBEEF);
    for _ in 0..5_000 {
        let r21 = rng.rotation();
        let r10 = rng.rotation();
        let mut c = PlateCircuit::new();
        c.add_link(const_link(2, 1, r21));
        c.add_link(const_link(1, 0, r10));
        let total = c.total_rotation(2, 0, AgeMa(100.0)).unwrap();
        let manual = r21.then(r10);
        assert!(total.angular_distance(manual) < 1e-10);
    }
}

#[test]
fn moving_equals_anchor_is_identity_always() {
    let c = PlateCircuit::new();
    for id in [0, 1, 701, 801, -5] {
        assert!(
            c.total_rotation(id, id, AgeMa(50.0))
                .unwrap()
                .angular_distance(Rotation::IDENTITY)
                < 1e-15
        );
    }
}
