//! Units and reference conventions for Lithora's kinematic core.
//!
//! Geodynamics mixes incompatible conventions freely, and silent unit
//! confusion is the dominant source of wrong plate-motion numbers. Every
//! quantity that leaves this crate carries an explicit convention in its
//! type or its documented contract:
//!
//! - Angles are radians internally. Degrees appear only at parse/display
//!   boundaries via [`Degrees`].
//! - Geological time is measured in millions of years before present (Ma),
//!   increasing into the past. Present day is `0.0`.
//! - Angular velocity is radians per million years internally; the common
//!   literature unit degrees/Myr is converted explicitly.
//! - Linear velocity on the surface is reported in millimetres per year,
//!   which is the standard geodetic unit. One mm/yr equals 1e-3 m/yr.
//! - Rotations follow the right-hand rule about the Euler axis and are
//!   interpreted as *active* rotations of points on the sphere unless a
//!   function documents otherwise.

/// Mean Earth radius in metres (spherical approximation, IUGG R1 arithmetic
/// mean of the WGS84 ellipsoid semi-axes). Used where a sphere is explicitly
/// assumed; ellipsoidal work uses [`crate::ellipsoid`].
pub const EARTH_RADIUS_M: f64 = 6_371_008.8;

/// Seconds in a Julian year, used when converting rates that are stored per
/// year into SI-adjacent intermediate quantities.
pub const SECONDS_PER_YEAR: f64 = 365.25 * 86_400.0;

/// An angle expressed in degrees. This is a boundary type: convert to radians
/// as early as possible and keep internal math in radians.
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct Degrees(pub f64);

impl Degrees {
    /// Convert to radians.
    #[inline]
    pub fn to_radians(self) -> f64 {
        self.0 * std::f64::consts::PI / 180.0
    }

    /// Build degrees from a radian value.
    #[inline]
    pub fn from_radians(rad: f64) -> Self {
        Degrees(rad * 180.0 / std::f64::consts::PI)
    }
}

/// Geological time in millions of years before present (Ma). Larger is older.
///
/// This newtype exists so that a reconstruction age cannot be accidentally
/// swapped with an angle, a rate, or a modern decimal-year epoch.
#[derive(Debug, Clone, Copy, PartialEq, PartialOrd)]
pub struct AgeMa(pub f64);

impl AgeMa {
    /// Present day.
    pub const PRESENT: AgeMa = AgeMa(0.0);

    /// Whether this age is the present (within a tight tolerance).
    #[inline]
    pub fn is_present(self) -> bool {
        self.0.abs() < 1e-9
    }
}

/// Convert an angular speed from degrees per million years to the internal
/// unit of radians per million years.
#[inline]
pub fn deg_per_myr_to_rad_per_myr(deg_per_myr: f64) -> f64 {
    deg_per_myr * std::f64::consts::PI / 180.0
}

/// Convert a surface linear speed from metres per year to millimetres per year.
#[inline]
pub fn m_per_yr_to_mm_per_yr(m_per_yr: f64) -> f64 {
    m_per_yr * 1000.0
}

/// Convert a surface linear speed from millimetres per year to metres per year.
#[inline]
pub fn mm_per_yr_to_m_per_yr(mm_per_yr: f64) -> f64 {
    mm_per_yr * 1e-3
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::f64::consts::PI;

    #[test]
    fn degrees_round_trip() {
        let d = Degrees(123.456);
        let back = Degrees::from_radians(d.to_radians());
        assert!((d.0 - back.0).abs() < 1e-12);
    }

    #[test]
    fn known_degree_values() {
        assert!((Degrees(180.0).to_radians() - PI).abs() < 1e-15);
        assert!((Degrees(90.0).to_radians() - PI / 2.0).abs() < 1e-15);
    }

    #[test]
    fn rate_conversion_is_pi_over_180() {
        let r = deg_per_myr_to_rad_per_myr(1.0);
        assert!((r - PI / 180.0).abs() < 1e-15);
    }

    #[test]
    fn mm_and_m_round_trip() {
        assert!((mm_per_yr_to_m_per_yr(m_per_yr_to_mm_per_yr(0.042)) - 0.042).abs() < 1e-15);
    }

    #[test]
    fn present_age_detection() {
        assert!(AgeMa::PRESENT.is_present());
        assert!(!AgeMa(10.0).is_present());
    }
}
