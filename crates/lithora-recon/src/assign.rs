//! Plate assignment by spherical-polygon containment.
//!
//! Reconstructing a point requires knowing which plate it belongs to. Given a
//! set of plate polygons, a point is assigned to the plate whose polygon
//! contains it. Two honest subtleties are handled explicitly: a point may fall
//! in no polygon (unassigned, which is reported rather than forced onto the
//! nearest plate), and a point may fall in more than one polygon where
//! polygons overlap at a shared boundary, in which case the ambiguity is
//! surfaced rather than silently resolved.
//!
//! This builds directly on the robust spherical containment in
//! [`lithora_geo::polygon`], so antimeridian and polar cases are handled.

use lithora_geo::coord::LatLon;
use lithora_geo::polygon::SphericalPolygon;

/// A named plate polygon.
pub struct PlatePolygon {
    pub plate_id: i64,
    pub polygon: SphericalPolygon,
}

/// The result of assigning a point to a plate.
#[derive(Debug, Clone, PartialEq)]
pub enum Assignment {
    /// Exactly one plate contains the point.
    Plate(i64),
    /// No plate polygon contains the point.
    Unassigned,
    /// More than one plate contains the point (overlap/ambiguity).
    Ambiguous(Vec<i64>),
}

/// Assign a point to a plate by containment over the given polygons.
pub fn assign(point: LatLon, plates: &[PlatePolygon]) -> Assignment {
    let hits: Vec<i64> = plates
        .iter()
        .filter(|p| p.polygon.contains(point))
        .map(|p| p.plate_id)
        .collect();
    match hits.len() {
        0 => Assignment::Unassigned,
        1 => Assignment::Plate(hits[0]),
        _ => Assignment::Ambiguous(hits),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use lithora_geo::polygon::SphericalRing;

    fn box_plate(id: i64, lat0: f64, lat1: f64, lon0: f64, lon1: f64) -> PlatePolygon {
        let ring = SphericalRing::from_latlon(&[
            LatLon::new(lat0, lon0),
            LatLon::new(lat0, lon1),
            LatLon::new(lat1, lon1),
            LatLon::new(lat1, lon0),
        ])
        .unwrap();
        PlatePolygon {
            plate_id: id,
            polygon: SphericalPolygon::new(ring),
        }
    }

    #[test]
    fn assigns_point_to_containing_plate() {
        let plates = vec![
            box_plate(101, -10.0, 10.0, -10.0, 10.0),
            box_plate(102, 20.0, 40.0, 20.0, 40.0),
        ];
        assert_eq!(
            assign(LatLon::new(0.0, 0.0), &plates),
            Assignment::Plate(101)
        );
        assert_eq!(
            assign(LatLon::new(30.0, 30.0), &plates),
            Assignment::Plate(102)
        );
    }

    #[test]
    fn unassigned_outside_all_plates() {
        let plates = vec![box_plate(101, -10.0, 10.0, -10.0, 10.0)];
        assert_eq!(
            assign(LatLon::new(80.0, 0.0), &plates),
            Assignment::Unassigned
        );
    }

    #[test]
    fn ambiguous_when_polygons_overlap() {
        let plates = vec![
            box_plate(101, -10.0, 10.0, -10.0, 10.0),
            box_plate(102, -5.0, 15.0, -5.0, 15.0), // overlaps the first
        ];
        match assign(LatLon::new(0.0, 0.0), &plates) {
            Assignment::Ambiguous(ids) => {
                assert!(ids.contains(&101) && ids.contains(&102));
            }
            other => panic!("expected ambiguous, got {other:?}"),
        }
    }
}
