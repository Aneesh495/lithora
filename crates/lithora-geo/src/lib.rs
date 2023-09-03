//! # lithora-geo
//!
//! The original spherical-geometry and plate-kinematics core of Lithora.
//!
//! This crate implements, from first principles, the mathematics that turns
//! published finite-rotation models into reconstructed geometry and present
//! day plate velocities:
//!
//! - [`units`]: explicit angle, time, and velocity conventions.
//! - [`vec3`]: the small Cartesian vector type used throughout.
//! - [`coord`]: geographic coordinates and the unit-sphere mapping.
//! - [`rotation`]: unit-quaternion finite rotations with stable composition.
//! - [`ellipsoid`]: the geodetic/geocentric distinction and WGS84 constants.
//! - [`sequence`]: piecewise finite-rotation interpolation over age samples.
//! - [`circuit`]: plate-circuit graph evaluation relative to an anchor.
//! - [`velocity`]: angular and linear surface velocities, `v = omega x r`.
//! - [`polygon`]: spherical polygon containment, area, and orientation.
//! - [`error`]: the error taxonomy separating bad input from unsupported
//!   requests.
//!
//! The guiding principle is that nothing silently averages away a geological
//! unknown: ages outside a model's range, missing circuit intervals, and
//! unsupported topologies surface as explicit errors rather than plausible
//! looking numbers.

pub mod circuit;
pub mod coord;
pub mod ellipsoid;
pub mod error;
pub mod polygon;
pub mod rotation;
pub mod sequence;
pub mod testutil;
pub mod units;
pub mod vec3;
pub mod velocity;

pub use coord::LatLon;
pub use error::{GeoError, Result};
pub use rotation::Rotation;
pub use units::{AgeMa, Degrees};
pub use vec3::Vec3;
