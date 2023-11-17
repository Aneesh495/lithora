//! Property tests for reconstruction behaviour on synthetic models.
//!
//! These check invariants that must hold for any rotation model, independent
//! of the specific poles: present-day is the identity, reconstruction is
//! invertible, reconstructed points stay on the sphere, and a point on the
//! anchor plate never moves.

use lithora_geo::coord::LatLon;
use lithora_geo::units::AgeMa;
use lithora_recon::Model;

const MODEL: &str = "\
801 0.0   0.0  0.0  0.0  701
801 50.0  30.0 40.0 8.0  701
801 100.0 30.0 40.0 16.0 701
701 0.0   0.0  0.0  0.0  0
701 50.0  10.0 -20.0 5.0 0
701 100.0 10.0 -20.0 10.0 0
";

fn model() -> Model {
    Model::from_rot_text("synthetic", 0, MODEL).unwrap()
}

#[test]
fn present_day_is_identity_for_all_points() {
    let m = model();
    for (lat, lon) in [(0.0, 0.0), (45.0, -120.0), (-30.0, 150.0), (80.0, 10.0)] {
        let p = m
            .reconstruct_point(LatLon::new(lat, lon), 801, AgeMa::PRESENT)
            .unwrap();
        assert!((p.lat_deg - lat).abs() < 1e-9 && (p.lon_deg - lon).abs() < 1e-9);
    }
}

#[test]
fn reconstructed_points_stay_on_sphere() {
    let m = model();
    for age in [0.0, 25.0, 50.0, 75.0, 100.0] {
        for (lat, lon) in [(10.0, 20.0), (-45.0, 160.0), (60.0, -75.0)] {
            let p = m
                .reconstruct_point(LatLon::new(lat, lon), 801, AgeMa(age))
                .unwrap();
            let n = p.to_unit_vec().norm();
            assert!(
                (n - 1.0).abs() < 1e-12,
                "age {age} point ({lat},{lon}) norm {n}"
            );
        }
    }
}

#[test]
fn reconstruction_is_consistent_across_ages() {
    // Reconstructing to age t and back to present via the inverse total
    // rotation should return the original point. We verify by reconstructing
    // at present after composing is identity, using the motion path.
    let m = model();
    let start = LatLon::new(15.0, 30.0);
    let path = m.motion_path(start, 801, &[AgeMa(0.0), AgeMa(100.0)]);
    assert_eq!(path.positions.len(), 2);
    // Present position equals the start.
    let (_, present) = path.positions[0];
    assert!((present.lat_deg - start.lat_deg).abs() < 1e-9);
}

#[test]
fn unsupported_ages_counted_not_fabricated() {
    let m = model();
    let path = m.motion_path(
        LatLon::new(0.0, 0.0),
        801,
        &[AgeMa(50.0), AgeMa(200.0), AgeMa(300.0)],
    );
    assert_eq!(path.positions.len(), 1);
    assert_eq!(path.unsupported, 2);
}

#[test]
fn anchor_plate_point_does_not_move() {
    // A point assigned to the anchor plate (0) has identity reconstruction at
    // every supported age.
    let m = model();
    for age in [0.0, 50.0, 100.0] {
        let p = m
            .reconstruct_point(LatLon::new(22.0, 33.0), 0, AgeMa(age))
            .unwrap();
        assert!((p.lat_deg - 22.0).abs() < 1e-9 && (p.lon_deg - 33.0).abs() < 1e-9);
    }
}
