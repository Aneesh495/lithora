//! # lithora-recon
//!
//! Rotation-file parsing and reconstruction orchestration built on top of
//! [`lithora_geo`]. This crate turns published finite-rotation models into
//! the reconstruction operations an atlas or command-line tool needs:
//! parsing `.rot` files, grouping them into plate-circuit links, and
//! reconstructing points, motion paths, and present-day velocities.
//!
//! It depends on the geometry core for all mathematics and adds only the
//! input/output and model-assembly layer.

pub mod compare;
pub mod reconstruct;
pub mod rot_format;

pub use compare::{compare_point, summarize, ComparisonPoint, ComparisonSummary};
pub use reconstruct::{Model, MotionPath};
