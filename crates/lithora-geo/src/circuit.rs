//! Plate-circuit evaluation.
//!
//! A rotation model is a forest of moving/fixed relationships: plate A moves
//! relative to its parent B, B relative to its parent C, and so on up to an
//! anchor (often plate 0, the spin axis / present-day mantle frame, or a
//! chosen fixed reference). The total reconstruction rotation of A relative
//! to the anchor at age `t` is the composition along the chain:
//!
//! ```text
//! R(A -> anchor, t) = R(A -> B, t) then R(B -> C, t) then ... then R(X -> anchor, t)
//! ```
//!
//! Each link is itself an interpolated finite rotation from a
//! [`RotationSequence`]. The composition order is temporal, matching
//! [`Rotation::then`]. Three things make this subtle and each is handled
//! explicitly here:
//!
//! - Parent relationships can change with age, so the graph is time
//!   dependent. We resolve the parent per age when evaluating.
//! - A link may have no sample covering the requested age; that is an
//!   unsupported request, surfaced as [`GeoError::NoBracket`] rather than
//!   silently skipped.
//! - Cycles in the declared graph are a parsing or data error and are
//!   detected rather than looped on forever.
//!
//! Changing the anchor must rotate every reconstructed point consistently;
//! this is verified in the tests by re-anchoring a toy circuit.

use crate::error::{GeoError, Result};
use crate::rotation::Rotation;
use crate::sequence::RotationSequence;
use crate::units::AgeMa;
use std::collections::{HashMap, HashSet};

/// A collection of rotation sequences keyed by moving plate id. For a given
/// moving plate we store the sequence and the fixed (parent) plate it is
/// expressed relative to. Real models allow the parent to change across age
/// intervals; this structure supports one parent per moving plate, which is
/// the documented rigid subset we certify. Multi-parent intervals are left
/// to a future extension and must not be silently approximated.
#[derive(Debug, Default)]
pub struct PlateCircuit {
    links: HashMap<i64, RotationSequence>,
}

impl PlateCircuit {
    pub fn new() -> Self {
        PlateCircuit { links: HashMap::new() }
    }

    /// Insert a link describing how `moving_plate` moves relative to its
    /// fixed parent. Overwrites any existing link for that moving plate.
    pub fn add_link(&mut self, seq: RotationSequence) {
        self.links.insert(seq.moving_plate, seq);
    }

    /// Number of plate links held.
    pub fn len(&self) -> usize {
        self.links.len()
    }

    pub fn is_empty(&self) -> bool {
        self.links.is_empty()
    }

    /// The fixed (parent) plate for a moving plate, if a link exists.
    fn parent_of(&self, plate: i64) -> Option<i64> {
        self.links.get(&plate).map(|s| s.fixed_plate)
    }

    /// Total reconstruction rotation of `moving` relative to `anchor` at age
    /// `t`, composing along the parent chain. The anchor need not be plate 0;
    /// any plate reachable along the chain works, and choosing a different
    /// anchor re-expresses the whole reconstruction in that frame.
    pub fn total_rotation(&self, moving: i64, anchor: i64, t: AgeMa) -> Result<Rotation> {
        if moving == anchor {
            return Ok(Rotation::IDENTITY);
        }
        let mut acc = Rotation::IDENTITY;
        let mut current = moving;
        let mut seen: HashSet<i64> = HashSet::new();
        loop {
            if !seen.insert(current) {
                return Err(GeoError::CircuitCycle(current));
            }
            let seq = self
                .links
                .get(&current)
                .ok_or(GeoError::NoCircuitPath { moving, anchor })?;
            // Interpolate this link at the requested age. An uncovered age
            // surfaces as an explicit error.
            let link_rot = seq.rotation_at(t)?;
            // Temporal composition: apply the link closer to the moving plate
            // first, then the ones nearer the anchor.
            acc = acc.then(link_rot);
            current = seq.fixed_plate;
            if current == anchor {
                return Ok(acc);
            }
            if self.parent_of(current).is_none() && current != anchor {
                // Reached a root that is not the requested anchor.
                return Err(GeoError::NoCircuitPath { moving, anchor });
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::coord::LatLon;
    use crate::sequence::PoleSample;
    use crate::vec3::Vec3;
    use std::f64::consts::PI;

    fn const_seq(moving: i64, fixed: i64, r: Rotation) -> RotationSequence {
        RotationSequence::new(
            moving,
            fixed,
            vec![
                PoleSample { age: AgeMa(0.0), rotation: Rotation::IDENTITY },
                PoleSample { age: AgeMa(100.0), rotation: r },
            ],
        )
        .unwrap()
    }

    #[test]
    fn two_plate_chain_composes() {
        // Plate 2 moves relative to 1 by 20 deg about z at 100 Ma;
        // plate 1 moves relative to anchor 0 by 10 deg about z.
        let r21 = Rotation::from_axis_angle(Vec3::new(0.0, 0.0, 1.0), 20f64.to_radians());
        let r10 = Rotation::from_axis_angle(Vec3::new(0.0, 0.0, 1.0), 10f64.to_radians());
        let mut c = PlateCircuit::new();
        c.add_link(const_seq(2, 1, r21));
        c.add_link(const_seq(1, 0, r10));
        let total = c.total_rotation(2, 0, AgeMa(100.0)).unwrap();
        // Same-axis rotations add: 30 deg about z.
        assert!((total.angle_rad() - 30f64.to_radians()).abs() < 1e-12);
    }

    #[test]
    fn noncommuting_three_plate_circuit() {
        // Different axes so order matters; verify against manual composition.
        let r32 = Rotation::from_euler_pole(LatLon::new(0.0, 0.0), 15.0);
        let r21 = Rotation::from_euler_pole(LatLon::new(90.0, 0.0), 25.0);
        let r10 = Rotation::from_euler_pole(LatLon::new(0.0, 90.0), 35.0);
        let mut c = PlateCircuit::new();
        c.add_link(const_seq(3, 2, r32));
        c.add_link(const_seq(2, 1, r21));
        c.add_link(const_seq(1, 0, r10));
        let total = c.total_rotation(3, 0, AgeMa(100.0)).unwrap();
        let manual = r32.then(r21).then(r10);
        assert!(total.angular_distance(manual) < 1e-12);
    }

    #[test]
    fn reanchoring_is_consistent() {
        // Reconstruct plate 2 relative to anchor 0, and relative to anchor 1.
        // The relationship total(2->0) = total(2->1) then total(1->0) must hold.
        let r21 = Rotation::from_euler_pole(LatLon::new(10.0, 20.0), 18.0);
        let r10 = Rotation::from_euler_pole(LatLon::new(-40.0, 100.0), 22.0);
        let mut c = PlateCircuit::new();
        c.add_link(const_seq(2, 1, r21));
        c.add_link(const_seq(1, 0, r10));
        let t = AgeMa(100.0);
        let to0 = c.total_rotation(2, 0, t).unwrap();
        let to1 = c.total_rotation(2, 1, t).unwrap();
        let one_to_zero = c.total_rotation(1, 0, t).unwrap();
        assert!(to0.angular_distance(to1.then(one_to_zero)) < 1e-12);
    }

    #[test]
    fn missing_path_is_an_error() {
        let mut c = PlateCircuit::new();
        c.add_link(const_seq(2, 1, Rotation::IDENTITY));
        // Plate 1 has no link to anchor 0.
        assert!(matches!(c.total_rotation(2, 0, AgeMa(50.0)), Err(GeoError::NoCircuitPath { .. })));
    }

    #[test]
    fn cycle_is_detected() {
        let mut c = PlateCircuit::new();
        c.add_link(const_seq(1, 2, Rotation::IDENTITY));
        c.add_link(const_seq(2, 1, Rotation::IDENTITY));
        assert!(matches!(c.total_rotation(1, 0, AgeMa(50.0)), Err(GeoError::CircuitCycle(_))));
    }

    #[test]
    fn age_beyond_link_range_is_rejected() {
        let mut c = PlateCircuit::new();
        c.add_link(const_seq(1, 0, Rotation::from_euler_pole(LatLon::new(0.0, 0.0), 5.0)));
        assert!(matches!(c.total_rotation(1, 0, AgeMa(200.0)), Err(GeoError::AgeOutOfRange { .. })));
    }

    #[test]
    fn anchor_equals_moving_is_identity() {
        let c = PlateCircuit::new();
        assert!(c.total_rotation(5, 5, AgeMa(10.0)).unwrap().angular_distance(Rotation::IDENTITY) < 1e-15);
    }
}
