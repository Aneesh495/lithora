//! Parser for the EarthByte/GPlates `.rot` rotation-file format.
//!
//! The format is one finite rotation per line:
//!
//! ```text
//! movingPlateID  age  lat  lon  angle  fixedPlateID  !comment
//! ```
//!
//! Each line states that, at `age` Ma, the moving plate is reconstructed to
//! the fixed plate by a finite rotation of `angle` degrees about the Euler
//! pole at (`lat`, `lon`). The present-day line (`age = 0`) is conventionally
//! the identity. Lines beginning with a comment marker or blank lines are
//! skipped. An angle and pole of a "cross-over" line can appear with the same
//! age and different fixed plate; we keep the association (moving, fixed) and
//! group samples per pair.
//!
//! This parser deliberately does not invent data: a malformed numeric field
//! is a hard error with line context, not a defaulted zero. The convention
//! choices (degrees, lat/lon pole, Ma, active rotation of the moving plate
//! toward the fixed plate's frame) are fixed here and documented so that no
//! downstream code has to guess.

use lithora_geo::coord::LatLon;
use lithora_geo::rotation::Rotation;
use lithora_geo::sequence::{PoleSample, RotationSequence};
use lithora_geo::units::AgeMa;
use std::collections::BTreeMap;
use thiserror::Error;

/// Error from parsing a rotation file.
#[derive(Debug, Error)]
pub enum RotParseError {
    #[error("line {line}: expected at least 6 fields, found {found}")]
    TooFewFields { line: usize, found: usize },
    #[error("line {line}: could not parse field '{field}' as a number")]
    BadNumber { line: usize, field: String },
    #[error("line {line}: latitude {lat} out of range [-90, 90]")]
    BadLatitude { line: usize, lat: f64 },
}

/// One parsed rotation record before grouping into sequences.
#[derive(Debug, Clone, Copy)]
pub struct RotRecord {
    pub moving_plate: i64,
    pub fixed_plate: i64,
    pub age: AgeMa,
    pub pole: LatLon,
    pub angle_deg: f64,
}

impl RotRecord {
    /// The finite rotation this record encodes.
    pub fn rotation(&self) -> Rotation {
        Rotation::from_euler_pole(self.pole, self.angle_deg)
    }
}

/// Parse the full text of a `.rot` file into records, preserving line order.
pub fn parse_rot(text: &str) -> Result<Vec<RotRecord>, RotParseError> {
    let mut out = Vec::new();
    for (idx, raw) in text.lines().enumerate() {
        let line = idx + 1;
        let content = strip_comment(raw);
        let trimmed = content.trim();
        if trimmed.is_empty() {
            continue;
        }
        let fields: Vec<&str> = trimmed.split_whitespace().collect();
        if fields.len() < 6 {
            return Err(RotParseError::TooFewFields {
                line,
                found: fields.len(),
            });
        }
        let moving_plate = parse_int(fields[0], line)?;
        let age = parse_f64(fields[1], line)?;
        let lat = parse_f64(fields[2], line)?;
        let lon = parse_f64(fields[3], line)?;
        let angle = parse_f64(fields[4], line)?;
        let fixed_plate = parse_int(fields[5], line)?;
        if !(-90.0..=90.0).contains(&lat) {
            return Err(RotParseError::BadLatitude { line, lat });
        }
        out.push(RotRecord {
            moving_plate,
            fixed_plate,
            age: AgeMa(age),
            pole: LatLon::new(lat, lon),
            angle_deg: angle,
        });
    }
    Ok(out)
}

/// Group parsed records into one [`RotationSequence`] per (moving, fixed)
/// pair, each sorted by age. Pairs with a single sample are retained; the
/// sequence layer handles single-sample interpolation.
pub fn group_sequences(records: &[RotRecord]) -> Vec<RotationSequence> {
    let mut by_pair: BTreeMap<(i64, i64), Vec<PoleSample>> = BTreeMap::new();
    for r in records {
        by_pair
            .entry((r.moving_plate, r.fixed_plate))
            .or_default()
            .push(PoleSample {
                age: r.age,
                rotation: r.rotation(),
            });
    }
    by_pair
        .into_iter()
        .filter_map(|((moving, fixed), samples)| RotationSequence::new(moving, fixed, samples).ok())
        .collect()
}

/// Remove a trailing comment introduced by `!` (GPlates convention) or `#`.
fn strip_comment(line: &str) -> &str {
    let bang = line.find('!').unwrap_or(line.len());
    let hash = line.find('#').unwrap_or(line.len());
    &line[..bang.min(hash)]
}

fn parse_int(s: &str, line: usize) -> Result<i64, RotParseError> {
    s.parse::<i64>()
        .or_else(|_| s.parse::<f64>().map(|v| v as i64))
        .map_err(|_| RotParseError::BadNumber {
            line,
            field: s.to_string(),
        })
}

fn parse_f64(s: &str, line: usize) -> Result<f64, RotParseError> {
    s.parse::<f64>().map_err(|_| RotParseError::BadNumber {
        line,
        field: s.to_string(),
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    const SAMPLE: &str = "\
# A tiny synthetic rotation file (not a real published model)
801  0.0   0.00   0.00   0.00  701  ! present day identity
801 10.0  20.00  30.00   5.00  701  ! moving 801 wrt 701
701  0.0   0.00   0.00   0.00    0
701 10.0 -10.00 110.00   3.00    0
";

    #[test]
    fn parses_expected_record_count() {
        let recs = parse_rot(SAMPLE).unwrap();
        assert_eq!(recs.len(), 4);
    }

    #[test]
    fn fields_map_correctly() {
        let recs = parse_rot(SAMPLE).unwrap();
        let r = recs[1];
        assert_eq!(r.moving_plate, 801);
        assert_eq!(r.fixed_plate, 701);
        assert!((r.age.0 - 10.0).abs() < 1e-12);
        assert!((r.pole.lat_deg - 20.0).abs() < 1e-12);
        assert!((r.angle_deg - 5.0).abs() < 1e-12);
    }

    #[test]
    fn present_day_is_identity_rotation() {
        let recs = parse_rot(SAMPLE).unwrap();
        assert!(recs[0].rotation().angular_distance(Rotation::IDENTITY) < 1e-12);
    }

    #[test]
    fn groups_into_two_pairs() {
        let seqs = group_sequences(&parse_rot(SAMPLE).unwrap());
        assert_eq!(seqs.len(), 2);
        for s in &seqs {
            assert_eq!(s.samples().len(), 2);
        }
    }

    #[test]
    fn comment_only_and_blank_lines_skipped() {
        let recs = parse_rot("\n   \n! just a comment\n").unwrap();
        assert!(recs.is_empty());
    }

    #[test]
    fn bad_latitude_rejected() {
        let err = parse_rot("801 0.0 95.0 0.0 0.0 701").unwrap_err();
        assert!(matches!(err, RotParseError::BadLatitude { .. }));
    }

    #[test]
    fn too_few_fields_rejected() {
        let err = parse_rot("801 0.0 0.0").unwrap_err();
        assert!(matches!(err, RotParseError::TooFewFields { .. }));
    }

    #[test]
    fn non_numeric_rejected() {
        let err = parse_rot("801 ten 0.0 0.0 0.0 701").unwrap_err();
        assert!(matches!(err, RotParseError::BadNumber { .. }));
    }
}
