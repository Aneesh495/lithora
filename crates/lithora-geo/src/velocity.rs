//! Plate velocities from finite rotations.
//!
//! Two velocity notions appear in this project and must not be conflated:
//!
//! 1. An *instantaneous* angular velocity `omega` (an Euler vector) gives the
//!    surface linear velocity at a point `r` by `v = omega x r`. This is the
//!    present-day plate velocity that GNSS observes.
//! 2. A *stage* rotation is the finite rotation carrying a plate from one
//!    age to another. Dividing the stage rotation's angle by the time span
//!    gives an average angular rate over that interval, which approaches the
//!    instantaneous `omega` only as the interval shrinks.
//!
//! We provide both: the exact cross-product velocity from an Euler vector,
//! and the stage angular velocity recovered from two bracketing total
//! reconstruction poles. The finite-difference stage velocity is validated
//! against the analytic cross product in the tests, which is the heart of
//! gate G03.

use crate::rotation::Rotation;
use crate::units::{AgeMa, EARTH_RADIUS_M};
use crate::vec3::Vec3;

/// An Euler vector: an angular velocity whose direction is the rotation axis
/// and whose magnitude is the angular rate in radians per million years.
#[derive(Debug, Clone, Copy)]
pub struct EulerVector {
    pub omega: Vec3,
}

impl EulerVector {
    /// Build from a pole axis (unit or not) and a rate in radians/Myr.
    pub fn from_axis_rate(axis: Vec3, rate_rad_per_myr: f64) -> Self {
        let a = axis.normalized().unwrap_or(Vec3::ZERO);
        EulerVector {
            omega: a.scale(rate_rad_per_myr),
        }
    }

    /// Instantaneous surface velocity at a unit-sphere position `r_hat`,
    /// returned as a Cartesian vector tangent to the sphere. Units: the
    /// `omega` magnitude is rad/Myr, so the returned vector has magnitude in
    /// (Earth radii) * (rad/Myr); multiply by Earth radius for a length rate.
    pub fn velocity_at(&self, r_hat: Vec3) -> Vec3 {
        self.omega.cross(r_hat)
    }

    /// Surface speed in millimetres per year at a unit position, on a sphere
    /// of the given radius (metres). This converts rad/Myr to mm/yr:
    /// `speed_m_per_myr = |omega x r| * R`, and 1 m/Myr = 1e-3 mm/yr since
    /// one million years has 1e6 years and one metre is 1e3 mm, so
    /// m/Myr * (1e3 mm/m) / (1e6 yr/Myr) = 1e-3 mm/yr.
    pub fn speed_mm_per_yr(&self, r_hat: Vec3, radius_m: f64) -> f64 {
        let v_rad = self.velocity_at(r_hat).norm(); // rad/Myr at unit radius
        let m_per_myr = v_rad * radius_m;
        m_per_myr * 1e-3
    }
}

/// The stage rotation from `t_old` to `t_young`: given total reconstruction
/// poles at both ages (each carrying present -> that age), the rotation that
/// carries the plate from its `t_old` position to its `t_young` position is
/// `R_young then R_old^-1` in our temporal-composition convention.
///
/// Equivalently it is `R_young * R_old^-1` as raw quaternion products; see
/// [`Rotation::then`] for why the method call reads reversed.
pub fn stage_rotation(r_old: Rotation, r_young: Rotation) -> Rotation {
    r_old.inverse().then(r_young)
}

/// Average angular velocity over a stage, as an Euler vector in rad/Myr.
/// Returns `None` when the two ages coincide (no interval).
pub fn stage_angular_velocity(
    r_old: Rotation,
    age_old: AgeMa,
    r_young: Rotation,
    age_young: AgeMa,
) -> Option<EulerVector> {
    let dt = age_old.0 - age_young.0;
    if dt.abs() < 1e-12 {
        return None;
    }
    let stage = stage_rotation(r_old, r_young);
    let axis = stage.axis()?;
    let rate = stage.angle_rad() / dt;
    Some(EulerVector {
        omega: axis.scale(rate),
    })
}

/// Linear surface velocity in mm/yr for a stage, at a unit position.
pub fn stage_speed_mm_per_yr(
    r_old: Rotation,
    age_old: AgeMa,
    r_young: Rotation,
    age_young: AgeMa,
    r_hat: Vec3,
) -> Option<f64> {
    let ev = stage_angular_velocity(r_old, age_old, r_young, age_young)?;
    Some(ev.speed_mm_per_yr(r_hat, EARTH_RADIUS_M))
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::f64::consts::PI;

    #[test]
    fn cross_product_velocity_is_perpendicular_to_position() {
        let ev = EulerVector::from_axis_rate(Vec3::new(0.0, 0.0, 1.0), 0.5);
        let r = Vec3::new(1.0, 0.0, 0.0);
        let v = ev.velocity_at(r);
        assert!(v.dot(r).abs() < 1e-15, "velocity must be tangent");
        // omega=0.5 about z at equator -> v = 0.5 in +y direction.
        assert!((v.y - 0.5).abs() < 1e-15 && v.x.abs() < 1e-15 && v.z.abs() < 1e-15);
    }

    #[test]
    fn velocity_vanishes_at_the_pole_of_rotation() {
        let ev = EulerVector::from_axis_rate(Vec3::new(0.0, 0.0, 1.0), 1.0);
        let at_pole = ev.velocity_at(Vec3::new(0.0, 0.0, 1.0));
        assert!(at_pole.norm() < 1e-15);
    }

    #[test]
    fn stage_rotation_composition() {
        // Young = 30 deg about z, old = 10 deg about z. Stage old->young is
        // 20 deg about z.
        let r_old = Rotation::from_axis_angle(Vec3::new(0.0, 0.0, 1.0), 10f64.to_radians());
        let r_young = Rotation::from_axis_angle(Vec3::new(0.0, 0.0, 1.0), 30f64.to_radians());
        let stage = stage_rotation(r_old, r_young);
        assert!((stage.angle_rad() - 20f64.to_radians()).abs() < 1e-12);
    }

    #[test]
    fn finite_difference_approaches_analytic_cross_product() {
        // A plate whose forward-time motion is +rate about +z. Forward time
        // runs from the older age toward present, so the point at the older
        // age sits "behind" by -rate*dt and the stage old->young advances it
        // by +rate*dt about +z. The recovered stage angular velocity must
        // then match the analytic Euler vector (+rate about +z) and produce
        // the same surface velocity v = omega x r.
        let rate = 0.02; // rad/Myr
        let r_hat = Vec3::new(1.0, 0.0, 0.0);
        let analytic = EulerVector::from_axis_rate(Vec3::new(0.0, 0.0, 1.0), rate);
        let v_analytic = analytic.velocity_at(r_hat);

        let dt = 1e-4;
        let r_young = Rotation::IDENTITY;
        // Older position is reached by rotating -rate*dt about +z from present.
        let r_old = Rotation::from_axis_angle(Vec3::new(0.0, 0.0, 1.0), -rate * dt);
        let ev = stage_angular_velocity(r_old, AgeMa(dt), r_young, AgeMa(0.0)).unwrap();
        let v_stage = ev.velocity_at(r_hat);
        assert!(
            v_stage.sub(v_analytic).norm() < 1e-9,
            "stage {v_stage:?} vs analytic {v_analytic:?}"
        );
    }

    #[test]
    fn mm_per_year_units_are_sane() {
        // A plate rotating ~1 deg/Myr about the pole has equatorial speed of
        // roughly 111 km/Myr = 111 mm/yr. Check the order of magnitude.
        let rate = PI / 180.0; // 1 deg/Myr in rad/Myr
        let ev = EulerVector::from_axis_rate(Vec3::new(0.0, 0.0, 1.0), rate);
        let speed = ev.speed_mm_per_yr(Vec3::new(1.0, 0.0, 0.0), EARTH_RADIUS_M);
        assert!((speed - 111.0).abs() < 2.0, "speed was {speed} mm/yr");
    }

    #[test]
    fn zero_interval_has_no_velocity() {
        assert!(stage_angular_velocity(
            Rotation::IDENTITY,
            AgeMa(5.0),
            Rotation::IDENTITY,
            AgeMa(5.0)
        )
        .is_none());
    }
}
