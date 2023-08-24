//! Reconstruction orchestration: from a parsed model to moved points.
//!
//! This ties the parser, the plate circuit, and the velocity math into the
//! operations an atlas or CLI actually asks for: reconstruct a point to an
//! age, trace its motion path over a set of ages, and report its present-day
//! stage velocity. A [`Model`] owns the circuit built from a rotation file
//! and exposes these as methods that return explicit errors when the model
//! does not support the request.

use lithora_geo::circuit::PlateCircuit;
use lithora_geo::coord::LatLon;
use lithora_geo::error::Result;
use lithora_geo::units::AgeMa;
use lithora_geo::velocity::stage_speed_mm_per_yr;

use crate::rot_format::{group_sequences, parse_rot, RotParseError};

/// A loaded reconstruction model: a named plate circuit plus the anchor plate
/// all reconstructions are expressed relative to.
#[derive(Debug)]
pub struct Model {
    pub name: String,
    pub anchor: i64,
    circuit: PlateCircuit,
}

impl Model {
    /// Build a model from the text of a rotation file. `anchor` is the plate
    /// every reconstruction is referenced to (commonly 0).
    pub fn from_rot_text(name: impl Into<String>, anchor: i64, text: &str) -> std::result::Result<Self, RotParseError> {
        let records = parse_rot(text)?;
        let mut circuit = PlateCircuit::new();
        for seq in group_sequences(&records) {
            circuit.add_link(seq);
        }
        Ok(Model { name: name.into(), anchor, circuit })
    }

    /// Number of plate links in the circuit.
    pub fn link_count(&self) -> usize {
        self.circuit.len()
    }

    /// Reconstruct a present-day point belonging to `plate` back to `age`.
    /// The point is given and returned in geographic coordinates.
    pub fn reconstruct_point(&self, point: LatLon, plate: i64, age: AgeMa) -> Result<LatLon> {
        let rot = self.circuit.total_rotation(plate, self.anchor, age)?;
        Ok(LatLon::from_vec(rot.apply(point.to_unit_vec())))
    }

    /// Trace a point's reconstructed position across a list of ages, skipping
    /// ages the model cannot support but reporting how many were dropped.
    pub fn motion_path(&self, point: LatLon, plate: i64, ages: &[AgeMa]) -> MotionPath {
        let mut positions = Vec::new();
        let mut unsupported = 0usize;
        for &age in ages {
            match self.reconstruct_point(point, plate, age) {
                Ok(p) => positions.push((age, p)),
                Err(_) => unsupported += 1,
            }
        }
        MotionPath { plate, positions, unsupported }
    }

    /// Present-day surface speed in mm/yr for a point on `plate`, estimated
    /// from a short stage of width `dt` Ma into the past. A small `dt`
    /// approaches the instantaneous velocity; the caller picks the scale.
    pub fn present_speed_mm_per_yr(&self, point: LatLon, plate: i64, dt_ma: f64) -> Result<f64> {
        let r_young = self.circuit.total_rotation(plate, self.anchor, AgeMa(0.0))?;
        let r_old = self.circuit.total_rotation(plate, self.anchor, AgeMa(dt_ma))?;
        Ok(stage_speed_mm_per_yr(r_old, AgeMa(dt_ma), r_young, AgeMa(0.0), point.to_unit_vec())
            .unwrap_or(0.0))
    }
}

/// A reconstructed motion path with provenance about unsupported ages.
#[derive(Debug)]
pub struct MotionPath {
    pub plate: i64,
    pub positions: Vec<(AgeMa, LatLon)>,
    pub unsupported: usize,
}

#[cfg(test)]
mod tests {
    use super::*;

    const MODEL: &str = "\
801 0.0  0.0  0.0 0.0 0
801 50.0 0.0  0.0 10.0 0
801 100.0 0.0 0.0 20.0 0
";

    #[test]
    fn present_day_point_unmoved() {
        let m = Model::from_rot_text("synthetic", 0, MODEL).unwrap();
        let p = m.reconstruct_point(LatLon::new(0.0, 30.0), 801, AgeMa(0.0)).unwrap();
        assert!((p.lat_deg).abs() < 1e-9 && (p.lon_deg - 30.0).abs() < 1e-9);
    }

    #[test]
    fn reconstruct_rotates_about_pole() {
        // Pole at (0,0) means rotation axis pierces the equator at lon 0.
        // A point at (0, 30) rotated 20 deg about that axis moves off the
        // equator. We just check the point actually moved and stayed on the
        // sphere.
        let m = Model::from_rot_text("synthetic", 0, MODEL).unwrap();
        let p0 = LatLon::new(0.0, 30.0);
        let p = m.reconstruct_point(p0, 801, AgeMa(100.0)).unwrap();
        let moved = p0.to_unit_vec().sub(p.to_unit_vec()).norm();
        assert!(moved > 1e-3, "point should have moved");
        assert!((p.to_unit_vec().norm() - 1.0).abs() < 1e-12);
    }

    #[test]
    fn motion_path_reports_unsupported() {
        let m = Model::from_rot_text("synthetic", 0, MODEL).unwrap();
        let ages = [AgeMa(0.0), AgeMa(50.0), AgeMa(100.0), AgeMa(300.0)];
        let path = m.motion_path(LatLon::new(0.0, 30.0), 801, &ages);
        assert_eq!(path.positions.len(), 3);
        assert_eq!(path.unsupported, 1);
    }

    #[test]
    fn present_speed_is_positive_for_moving_plate() {
        let m = Model::from_rot_text("synthetic", 0, MODEL).unwrap();
        let speed = m.present_speed_mm_per_yr(LatLon::new(0.0, 90.0), 801, 1.0).unwrap();
        assert!(speed > 0.0);
    }
}
