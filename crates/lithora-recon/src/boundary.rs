//! Plate-boundary classification and relative motion (capability L09).
//!
//! Where a model provides boundary topology, the relative motion of the two
//! plates meeting at a boundary segment can be decomposed into a
//! boundary-normal component (convergence or divergence) and a
//! boundary-parallel component (transform/strike-slip), and the segment
//! classified accordingly. Where the topology is NOT available, this module
//! reports the classification as unavailable rather than guessing, because a
//! rigid-polygon subset does not carry the boundary geometry needed to do it
//! honestly.
//!
//! The relative-motion decomposition itself is exact given two plates' Euler
//! vectors and a boundary point and local strike: the relative Euler vector is
//! the difference of the two, its surface velocity at the point is
//! `v = omega_rel x r`, and that velocity projects onto the strike and its
//! normal. We expose that decomposition and a classifier; whether the strike
//! is known is the caller's (the model's) responsibility to supply.

use lithora_geo::coord::LatLon;
use lithora_geo::vec3::Vec3;
use lithora_geo::velocity::EulerVector;

/// How a boundary segment moves, once relative motion is known.
#[derive(Debug, Clone, PartialEq)]
pub enum BoundaryClass {
    /// Plates move apart across the boundary (normal component positive).
    Divergent,
    /// Plates move together across the boundary (normal component negative).
    Convergent,
    /// Motion is mostly along the boundary (parallel dominates).
    Transform,
    /// Topology or strike not available; classification cannot be made.
    Unavailable,
}

/// Relative motion of two plates at a boundary point, decomposed.
#[derive(Debug, Clone)]
pub struct RelativeMotion {
    /// Component along the boundary strike (mm/yr); sign follows the strike.
    pub parallel_mm_yr: f64,
    /// Component across the boundary (mm/yr); positive is divergent.
    pub normal_mm_yr: f64,
    pub class: BoundaryClass,
}

/// Decompose the relative motion of two plates at a boundary point.
///
/// `omega_a` and `omega_b` are the plates' Euler vectors; the boundary point is
/// `point`; `strike` is a unit tangent vector along the boundary at the point
/// (east/north embedded in 3D). If `strike` is `None` (topology absent), the
/// classification is `Unavailable` and the components are reported as NaN.
pub fn relative_motion(
    omega_a: EulerVector,
    omega_b: EulerVector,
    point: LatLon,
    strike: Option<Vec3>,
    radius_m: f64,
) -> RelativeMotion {
    let r = point.to_unit_vec();
    // Relative Euler vector and its surface velocity at the point.
    let omega_rel = EulerVector {
        omega: omega_a.omega.sub(omega_b.omega),
    };
    let v_rad = omega_rel.velocity_at(r); // rad/Myr at unit radius
    let v_mm = v_rad.scale(radius_m * 1e-3); // mm/yr

    let strike = match strike {
        Some(s) => match s.normalized() {
            Some(sn) => sn,
            None => return unavailable(),
        },
        None => return unavailable(),
    };
    // Boundary normal in the tangent plane: perpendicular to both the strike
    // and the outward radial direction.
    let normal = match r.cross(strike).normalized() {
        Some(n) => n,
        None => return unavailable(),
    };

    let parallel = v_mm.dot(strike);
    let across = v_mm.dot(normal);
    let class = if across.abs() >= parallel.abs() {
        if across > 0.0 {
            BoundaryClass::Divergent
        } else {
            BoundaryClass::Convergent
        }
    } else {
        BoundaryClass::Transform
    };
    RelativeMotion {
        parallel_mm_yr: parallel,
        normal_mm_yr: across,
        class,
    }
}

fn unavailable() -> RelativeMotion {
    RelativeMotion {
        parallel_mm_yr: f64::NAN,
        normal_mm_yr: f64::NAN,
        class: BoundaryClass::Unavailable,
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use lithora_geo::units::EARTH_RADIUS_M;

    #[test]
    fn unavailable_without_strike() {
        let a = EulerVector::from_axis_rate(Vec3::new(0.0, 0.0, 1.0), 0.01);
        let b = EulerVector::from_axis_rate(Vec3::new(0.0, 0.0, 1.0), 0.005);
        let rm = relative_motion(a, b, LatLon::new(0.0, 0.0), None, EARTH_RADIUS_M);
        assert_eq!(rm.class, BoundaryClass::Unavailable);
        assert!(rm.parallel_mm_yr.is_nan());
    }

    #[test]
    fn transform_when_motion_is_along_strike() {
        // Two plates rotating about the z axis at different rates: at the
        // equator their relative velocity is purely east (along a N-S strike
        // it is parallel -> transform).
        let a = EulerVector::from_axis_rate(Vec3::new(0.0, 0.0, 1.0), 0.02);
        let b = EulerVector::from_axis_rate(Vec3::new(0.0, 0.0, 1.0), 0.01);
        let point = LatLon::new(0.0, 0.0); // r = +x, relative v is +y (east)
        let strike = Vec3::new(0.0, 1.0, 0.0); // along east
        let rm = relative_motion(a, b, point, Some(strike), EARTH_RADIUS_M);
        assert_eq!(rm.class, BoundaryClass::Transform);
        assert!(rm.parallel_mm_yr.abs() > rm.normal_mm_yr.abs());
    }

    #[test]
    fn divergent_when_motion_is_across_strike() {
        // Same plates, but a strike along north means the east-directed
        // relative velocity is across the boundary -> divergent/convergent.
        let a = EulerVector::from_axis_rate(Vec3::new(0.0, 0.0, 1.0), 0.02);
        let b = EulerVector::from_axis_rate(Vec3::new(0.0, 0.0, 1.0), 0.01);
        let point = LatLon::new(0.0, 0.0);
        let strike = Vec3::new(0.0, 0.0, 1.0); // along north (z at equator)
        let rm = relative_motion(a, b, point, Some(strike), EARTH_RADIUS_M);
        assert!(matches!(
            rm.class,
            BoundaryClass::Divergent | BoundaryClass::Convergent
        ));
        assert!(rm.normal_mm_yr.abs() > rm.parallel_mm_yr.abs());
    }
}
