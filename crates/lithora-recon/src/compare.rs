//! Cross-model reconstruction comparison (capability L08).
//!
//! Two published rotation models reconstructing the same point at the same age
//! and anchor generally disagree, and that disagreement is evidence about how
//! poorly deep-time plate positions are constrained. This module compares two
//! [`Model`]s at matched inputs and reports the angular disagreement, never
//! averaging them into a single false "truth".
//!
//! A comparison is only valid where both models can answer the query. If
//! either model lacks the plate, the age, or the circuit path, the comparison
//! for that input is reported as unavailable rather than silently dropped or
//! filled in.

use lithora_geo::coord::LatLon;
use lithora_geo::units::AgeMa;

use crate::reconstruct::Model;

/// The outcome of comparing two models at one (point, plate, age).
#[derive(Debug, Clone)]
pub enum ComparisonPoint {
    /// Both models reconstructed the point; the angular difference in radians
    /// and both reconstructed positions are reported.
    Compared {
        age: AgeMa,
        angular_diff_rad: f64,
        pos_a: LatLon,
        pos_b: LatLon,
    },
    /// At least one model could not answer; which side failed is recorded.
    Unavailable { age: AgeMa, reason: String },
}

/// Summary statistics over a set of comparison points.
#[derive(Debug, Clone)]
pub struct ComparisonSummary {
    pub n_compared: usize,
    pub n_unavailable: usize,
    pub max_angular_diff_rad: f64,
    pub mean_angular_diff_rad: f64,
}

/// Compare two models for one point across a set of ages. The plate id must be
/// the same in both models for the comparison to be meaningful; the caller is
/// responsible for supplying a plate both models define.
pub fn compare_point(
    model_a: &Model,
    model_b: &Model,
    point: LatLon,
    plate: i64,
    ages: &[AgeMa],
) -> Vec<ComparisonPoint> {
    let mut out = Vec::with_capacity(ages.len());
    for &age in ages {
        let a = model_a.reconstruct_point(point, plate, age);
        let b = model_b.reconstruct_point(point, plate, age);
        match (a, b) {
            (Ok(pa), Ok(pb)) => {
                let diff = pa.to_unit_vec().angle_to(pb.to_unit_vec());
                out.push(ComparisonPoint::Compared {
                    age,
                    angular_diff_rad: diff,
                    pos_a: pa,
                    pos_b: pb,
                });
            }
            (Err(e), _) => out.push(ComparisonPoint::Unavailable {
                age,
                reason: format!("model A: {e}"),
            }),
            (_, Err(e)) => out.push(ComparisonPoint::Unavailable {
                age,
                reason: format!("model B: {e}"),
            }),
        }
    }
    out
}

/// Summarise a comparison, counting compared and unavailable points and
/// reporting the maximum and mean angular disagreement over the compared ones.
pub fn summarize(points: &[ComparisonPoint]) -> ComparisonSummary {
    let mut n_compared = 0usize;
    let mut n_unavailable = 0usize;
    let mut max_diff = 0.0_f64;
    let mut sum_diff = 0.0_f64;
    for p in points {
        match p {
            ComparisonPoint::Compared {
                angular_diff_rad, ..
            } => {
                n_compared += 1;
                max_diff = max_diff.max(*angular_diff_rad);
                sum_diff += *angular_diff_rad;
            }
            ComparisonPoint::Unavailable { .. } => n_unavailable += 1,
        }
    }
    ComparisonSummary {
        n_compared,
        n_unavailable,
        max_angular_diff_rad: max_diff,
        mean_angular_diff_rad: if n_compared > 0 {
            sum_diff / n_compared as f64
        } else {
            0.0
        },
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    // Two synthetic models that agree at present but diverge with age because
    // their Euler poles differ.
    const MODEL_A: &str = "\
801 0.0   0.0  0.0  0.0  0
801 50.0  30.0 40.0 8.0  0
801 100.0 30.0 40.0 16.0 0
";
    const MODEL_B: &str = "\
801 0.0   0.0  0.0  0.0  0
801 50.0  10.0 -20.0 8.0 0
801 100.0 10.0 -20.0 16.0 0
";

    fn models() -> (Model, Model) {
        (
            Model::from_rot_text("A", 0, MODEL_A).unwrap(),
            Model::from_rot_text("B", 0, MODEL_B).unwrap(),
        )
    }

    #[test]
    fn agreement_at_present_divergence_with_age() {
        let (a, b) = models();
        let pts = compare_point(
            &a,
            &b,
            LatLon::new(5.0, 20.0),
            801,
            &[AgeMa(0.0), AgeMa(50.0), AgeMa(100.0)],
        );
        if let ComparisonPoint::Compared {
            angular_diff_rad, ..
        } = &pts[0]
        {
            assert!(*angular_diff_rad < 1e-9, "models must agree at present");
        } else {
            panic!("expected a comparison at present");
        }
        // Disagreement grows with age.
        let d50 = match &pts[1] {
            ComparisonPoint::Compared {
                angular_diff_rad, ..
            } => *angular_diff_rad,
            _ => panic!(),
        };
        let d100 = match &pts[2] {
            ComparisonPoint::Compared {
                angular_diff_rad, ..
            } => *angular_diff_rad,
            _ => panic!(),
        };
        assert!(d100 > d50 && d50 > 0.0, "disagreement should grow with age");
    }

    #[test]
    fn unavailable_age_is_reported_not_dropped() {
        let (a, b) = models();
        let pts = compare_point(&a, &b, LatLon::new(5.0, 20.0), 801, &[AgeMa(200.0)]);
        assert!(matches!(pts[0], ComparisonPoint::Unavailable { .. }));
    }

    #[test]
    fn summary_counts_and_stats() {
        let (a, b) = models();
        let pts = compare_point(
            &a,
            &b,
            LatLon::new(5.0, 20.0),
            801,
            &[AgeMa(0.0), AgeMa(100.0), AgeMa(300.0)],
        );
        let s = summarize(&pts);
        assert_eq!(s.n_compared, 2);
        assert_eq!(s.n_unavailable, 1);
        assert!(s.max_angular_diff_rad >= s.mean_angular_diff_rad);
    }
}
