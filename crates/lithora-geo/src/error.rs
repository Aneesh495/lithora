//! Error types for the geometry and kinematics core.
//!
//! The core distinguishes between inputs that are malformed (a bad rotation
//! file, an out-of-range latitude) and requests that are well formed but
//! unsupported by the available data (reconstructing past a model's valid
//! age, a plate circuit with a missing interval). Collapsing these into one
//! bucket hides the difference between "fix your file" and "this model cannot
//! answer that question", which matters for geological honesty.

use thiserror::Error;

/// Errors raised by the geometry and reconstruction core.
#[derive(Debug, Error)]
pub enum GeoError {
    /// A latitude outside `[-90, 90]` or a non-finite coordinate.
    #[error("invalid coordinate: {0}")]
    InvalidCoord(String),

    /// A plate circuit referenced a plate with no path to the anchor.
    #[error("no rotation path from plate {moving} to anchor {anchor}")]
    NoCircuitPath { moving: i64, anchor: i64 },

    /// A cycle was detected while chaining the plate circuit.
    #[error("cycle detected in plate circuit at plate {0}")]
    CircuitCycle(i64),

    /// A requested reconstruction age lies outside the model's valid range.
    #[error("age {age} Ma is outside supported range [{min}, {max}] Ma")]
    AgeOutOfRange { age: f64, min: f64, max: f64 },

    /// Interpolation requested between samples that do not bracket the age.
    #[error("cannot interpolate rotation at age {0} Ma: no bracketing samples")]
    NoBracket(f64),

    /// A rotation sequence had fewer than the samples required to interpolate.
    #[error("rotation sequence for plate {0} has too few samples")]
    EmptySequence(i64),

    /// A parse failure in a rotation or polygon file, with line context.
    #[error("parse error at line {line}: {message}")]
    Parse { line: usize, message: String },
}

/// Convenience result alias for the core.
pub type Result<T> = std::result::Result<T, GeoError>;
