//! Spherical polygons: containment, area, and orientation.
//!
//! Plate polygons are closed rings of (lat, lon) vertices on the sphere.
//! Point-in-polygon on a sphere is subtler than on a plane: a ring can wrap
//! across the antimeridian, enclose a pole, and its "inside" is whichever of
//! the two regions the winding implies. We compute containment with the
//! spherical winding number (sum of signed angles subtended at the test
//! point), which is robust to antimeridian wrap because it works in 3D on
//! unit vectors and never reasons about raw longitude jumps.
//!
//! Area uses the spherical excess via L'Huilier's theorem summed over a fan
//! of triangles from the first vertex. Orientation (clockwise vs
//! counter-clockwise as seen from outside) follows the sign of the signed
//! area, which also tells us which side is "inside" for winding.

use crate::coord::LatLon;
use crate::units::EARTH_RADIUS_M;
use crate::vec3::Vec3;

/// A closed spherical ring. Vertices are stored as unit vectors; the ring is
/// implicitly closed (last connects to first). Holes are represented as
/// separate rings in [`SphericalPolygon`].
#[derive(Debug, Clone)]
pub struct SphericalRing {
    verts: Vec<Vec3>,
}

impl SphericalRing {
    /// Build from geographic vertices. A trailing vertex equal to the first
    /// is dropped so the ring is stored once. Requires at least 3 distinct
    /// vertices to bound an area.
    pub fn from_latlon(points: &[LatLon]) -> Option<Self> {
        let mut verts: Vec<Vec3> = points.iter().map(|p| p.to_unit_vec()).collect();
        if verts.len() >= 2 {
            let first = verts[0];
            let last = verts[verts.len() - 1];
            if first.sub(last).norm() < 1e-12 {
                verts.pop();
            }
        }
        if verts.len() < 3 {
            None
        } else {
            Some(SphericalRing { verts })
        }
    }

    pub fn vertices(&self) -> &[Vec3] {
        &self.verts
    }

    /// Signed spherical area in steradians. Positive for a counter-clockwise
    /// ring as seen from outside the sphere (right-hand rule about the
    /// outward normal). The sign encodes orientation.
    pub fn signed_area_steradians(&self) -> f64 {
        // Use the spherical polygon area as the sum over edges of the
        // exterior turning, equivalently via the Girard excess. We sum the
        // signed areas of triangles (v0, vi, vi+1) using the formula with
        // the triple product and dot products, which keeps the sign.
        let v0 = self.verts[0];
        let mut area = 0.0;
        for i in 1..self.verts.len() - 1 {
            area += signed_triangle_area(v0, self.verts[i], self.verts[i + 1]);
        }
        area
    }

    /// Unsigned area on a sphere of the given radius (metres), in square
    /// metres. Uses the absolute spherical excess so orientation does not
    /// flip the magnitude.
    pub fn area_m2(&self, radius_m: f64) -> f64 {
        self.signed_area_steradians().abs() * radius_m * radius_m
    }

    /// Whether a point lies inside the ring, by spherical winding number.
    ///
    /// We sum the signed solid angle the ring subtends at the test point,
    /// triangle by triangle, using the spherical excess of `(p, v_i,
    /// v_{i+1})`. For a point enclosed by the ring the signed total is
    /// `+/- 2*pi`; for a point outside (including the antipode of an
    /// enclosed point) it is near `0`. We split at `pi`, which the two
    /// possible totals straddle cleanly.
    ///
    /// Working with spherical triangle areas instead of a tangent-plane
    /// projection avoids the degeneracy where vertices near the antipode of
    /// `p` project to tiny vectors whose directions wind spuriously.
    pub fn contains(&self, point: LatLon) -> bool {
        let p = point.to_unit_vec();
        let n = self.verts.len();
        let mut solid_angle = 0.0;
        for i in 0..n {
            solid_angle += edge_dihedral_at(p, self.verts[i], self.verts[(i + 1) % n]);
        }
        // A closed ring divides the sphere into two regions; the dihedral sum
        // is close to +2*pi for points in one region and -2*pi for the other.
        // Which region is the intended interior is set by the ring's winding:
        // a counter-clockwise ring (positive signed area) encloses the region
        // that subtends +2*pi. We therefore test the sign, not just the
        // magnitude, so the antipodal region of a small patch reads as
        // outside rather than as a second interior.
        let orient = self.signed_area_steradians().signum();
        let threshold = std::f64::consts::PI;
        orient * solid_angle > threshold
    }
}

/// A spherical polygon: one outer ring plus zero or more holes. A point is
/// inside the polygon when it is inside the outer ring and inside none of the
/// holes.
#[derive(Debug, Clone)]
pub struct SphericalPolygon {
    pub outer: SphericalRing,
    pub holes: Vec<SphericalRing>,
}

impl SphericalPolygon {
    pub fn new(outer: SphericalRing) -> Self {
        SphericalPolygon { outer, holes: Vec::new() }
    }

    pub fn with_hole(mut self, hole: SphericalRing) -> Self {
        self.holes.push(hole);
        self
    }

    pub fn contains(&self, point: LatLon) -> bool {
        if !self.outer.contains(point) {
            return false;
        }
        !self.holes.iter().any(|h| h.contains(point))
    }

    /// Net area in square metres: outer minus holes.
    pub fn area_m2(&self) -> f64 {
        let mut a = self.outer.area_m2(EARTH_RADIUS_M);
        for h in &self.holes {
            a -= h.area_m2(EARTH_RADIUS_M);
        }
        a.max(0.0)
    }
}

/// Signed angle that the great-circle edge from `a` to `b` subtends at the
/// viewpoint `p`, measured on the sphere. Summed over a closed ring this
/// gives the signed solid angle the ring encloses as seen from `p`: `2*pi`
/// when `p` is inside, `0` when outside.
///
/// The numerator `(a x b) . p` is the oriented "sweep" of the edge about `p`;
/// the denominator `a.b - (a.p)(b.p)` is the cosine of the dihedral. Using
/// `atan2` of these two keeps the sign and stays well conditioned even when
/// `a` or `b` is near the antipode of `p`, where a tangent-plane projection
/// would collapse.
fn edge_dihedral_at(p: Vec3, a: Vec3, b: Vec3) -> f64 {
    let num = a.cross(b).dot(p);
    let den = a.dot(b) - a.dot(p) * b.dot(p);
    num.atan2(den)
}

/// Signed area of a spherical triangle in steradians, positive when the
/// vertices wind counter-clockwise as seen from outside. Uses the spherical
/// excess from the three interior angles with a sign from the triple product.
fn signed_triangle_area(a: Vec3, b: Vec3, c: Vec3) -> f64 {
    // Interior angles via the spherical law for the angle at each vertex.
    let excess = spherical_excess(a, b, c);
    let sign = a.cross(b).dot(c).signum();
    sign * excess
}

/// Spherical excess (unsigned) of the triangle with the given unit-vector
/// vertices, computed with a numerically stable half-angle (L'Huilier) form.
fn spherical_excess(a: Vec3, b: Vec3, c: Vec3) -> f64 {
    let side_a = b.angle_to(c);
    let side_b = c.angle_to(a);
    let side_c = a.angle_to(b);
    let s = 0.5 * (side_a + side_b + side_c);
    let t = (0.5 * s).tan()
        * (0.5 * (s - side_a)).tan()
        * (0.5 * (s - side_b)).tan()
        * (0.5 * (s - side_c)).tan();
    let t = t.max(0.0);
    4.0 * t.sqrt().atan()
}

/// Great-circle distance between two points on a sphere of the given radius
/// (metres). Uses the `atan2` form for stability at small and large angles.
pub fn great_circle_distance_m(a: LatLon, b: LatLon, radius_m: f64) -> f64 {
    a.to_unit_vec().angle_to(b.to_unit_vec()) * radius_m
}

#[cfg(test)]
mod tests {
    use super::*;

    fn square_around_equator() -> SphericalRing {
        // A box spanning lon [-10,10], lat [-10,10].
        SphericalRing::from_latlon(&[
            LatLon::new(-10.0, -10.0),
            LatLon::new(-10.0, 10.0),
            LatLon::new(10.0, 10.0),
            LatLon::new(10.0, -10.0),
        ])
        .unwrap()
    }

    #[test]
    fn point_inside_and_outside() {
        let ring = square_around_equator();
        assert!(ring.contains(LatLon::new(0.0, 0.0)));
        assert!(!ring.contains(LatLon::new(0.0, 40.0)));
        assert!(!ring.contains(LatLon::new(50.0, 0.0)));
    }

    #[test]
    fn antimeridian_spanning_ring() {
        // A box from lon 170 to -170 (crossing the dateline) around lat 0.
        let ring = SphericalRing::from_latlon(&[
            LatLon::new(-10.0, 170.0),
            LatLon::new(-10.0, -170.0),
            LatLon::new(10.0, -170.0),
            LatLon::new(10.0, 170.0),
        ])
        .unwrap();
        assert!(ring.contains(LatLon::new(0.0, 180.0)), "point on dateline should be inside");
        assert!(!ring.contains(LatLon::new(0.0, 0.0)), "antipodal point should be outside");
    }

    #[test]
    fn polar_cap_contains_pole() {
        // A ring near 80 N encloses the north pole.
        let ring = SphericalRing::from_latlon(&[
            LatLon::new(80.0, 0.0),
            LatLon::new(80.0, 90.0),
            LatLon::new(80.0, 180.0),
            LatLon::new(80.0, -90.0),
        ])
        .unwrap();
        assert!(ring.contains(LatLon::new(89.0, 0.0)), "pole region inside the cap");
        assert!(!ring.contains(LatLon::new(0.0, 0.0)), "equator outside the cap");
    }

    #[test]
    fn area_of_hemisphere_box_is_positive_and_bounded() {
        let ring = square_around_equator();
        let area = ring.area_m2(EARTH_RADIUS_M);
        // Should be a modest positive area, far below a full hemisphere.
        let hemisphere = 2.0 * std::f64::consts::PI * EARTH_RADIUS_M * EARTH_RADIUS_M;
        assert!(area > 0.0 && area < hemisphere);
    }

    #[test]
    fn orientation_sign_flips_when_reversed() {
        let fwd = square_around_equator();
        let rev = SphericalRing::from_latlon(&[
            LatLon::new(10.0, -10.0),
            LatLon::new(10.0, 10.0),
            LatLon::new(-10.0, 10.0),
            LatLon::new(-10.0, -10.0),
        ])
        .unwrap();
        let sa = fwd.signed_area_steradians();
        let sb = rev.signed_area_steradians();
        assert!(sa * sb < 0.0, "reversed ring must have opposite signed area");
    }

    #[test]
    fn holes_exclude_their_interior() {
        let outer = square_around_equator();
        let hole = SphericalRing::from_latlon(&[
            LatLon::new(-2.0, -2.0),
            LatLon::new(-2.0, 2.0),
            LatLon::new(2.0, 2.0),
            LatLon::new(2.0, -2.0),
        ])
        .unwrap();
        let poly = SphericalPolygon::new(outer).with_hole(hole);
        assert!(poly.contains(LatLon::new(5.0, 5.0)), "between hole and outer");
        assert!(!poly.contains(LatLon::new(0.0, 0.0)), "inside the hole");
    }

    #[test]
    fn great_circle_quarter_arc() {
        // From (0,0) to (0,90) is a quarter of the great circle.
        let d = great_circle_distance_m(LatLon::new(0.0, 0.0), LatLon::new(0.0, 90.0), EARTH_RADIUS_M);
        let quarter = 0.5 * std::f64::consts::PI * EARTH_RADIUS_M;
        assert!((d - quarter).abs() < 1.0);
    }

    #[test]
    fn degenerate_ring_rejected() {
        assert!(SphericalRing::from_latlon(&[LatLon::new(0.0, 0.0), LatLon::new(1.0, 1.0)]).is_none());
    }
}
