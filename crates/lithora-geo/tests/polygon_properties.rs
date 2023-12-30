//! Property tests for spherical polygon area, orientation, and containment.
//!
//! These confirm invariants over many random convex rings: reversing a ring
//! flips the sign of its signed area but not its magnitude, a ring's own
//! centroid direction is inside it, and containment is stable under a global
//! rotation of the whole configuration (the ring and the test point rotate
//! together, so containment must not change).

use lithora_geo::coord::LatLon;
use lithora_geo::polygon::SphericalRing;
use lithora_geo::rotation::Rotation;
use lithora_geo::testutil::Rng;

fn small_quad(rng: &mut Rng) -> (LatLon, Vec<LatLon>) {
    // A small axis-aligned quad around a random center, kept away from the
    // poles so the box is well formed.
    let center = LatLon::new(rng.range(-70.0, 70.0), rng.range(-180.0, 180.0));
    let h = rng.range(1.0, 6.0);
    let verts = vec![
        LatLon::new(center.lat_deg - h, center.lon_deg - h),
        LatLon::new(center.lat_deg - h, center.lon_deg + h),
        LatLon::new(center.lat_deg + h, center.lon_deg + h),
        LatLon::new(center.lat_deg + h, center.lon_deg - h),
    ];
    (center, verts)
}

#[test]
fn reversing_ring_flips_signed_area_sign_only() {
    let mut rng = Rng::new(1);
    for _ in 0..3_000 {
        let (_, verts) = small_quad(&mut rng);
        let fwd = match SphericalRing::from_latlon(&verts) {
            Some(r) => r,
            None => continue,
        };
        let mut rev = verts.clone();
        rev.reverse();
        let back = SphericalRing::from_latlon(&rev).unwrap();
        let a = fwd.signed_area_steradians();
        let b = back.signed_area_steradians();
        assert!(a * b < 0.0, "reversed ring should flip sign");
        assert!((a.abs() - b.abs()).abs() < 1e-12, "magnitude should match");
    }
}

#[test]
fn center_is_inside_its_own_box() {
    let mut rng = Rng::new(2);
    for _ in 0..3_000 {
        let (center, verts) = small_quad(&mut rng);
        if let Some(ring) = SphericalRing::from_latlon(&verts) {
            assert!(ring.contains(center), "center should be inside its box");
        }
    }
}

#[test]
fn containment_is_rotation_invariant() {
    // Rotating the ring and the test point by the same rotation must not
    // change whether the point is inside.
    let mut rng = Rng::new(3);
    for _ in 0..2_000 {
        let (center, verts) = small_quad(&mut rng);
        let ring = match SphericalRing::from_latlon(&verts) {
            Some(r) => r,
            None => continue,
        };
        let inside_before = ring.contains(center);

        let rot = rng.rotation();
        let rotated_verts: Vec<LatLon> = verts
            .iter()
            .map(|v| LatLon::from_vec(rot.apply(v.to_unit_vec())))
            .collect();
        let rotated_ring = match SphericalRing::from_latlon(&rotated_verts) {
            Some(r) => r,
            None => continue,
        };
        let rotated_center = LatLon::from_vec(rot.apply(center.to_unit_vec()));
        let inside_after = rotated_ring.contains(rotated_center);
        assert_eq!(
            inside_before, inside_after,
            "containment changed under rotation"
        );
    }
}
