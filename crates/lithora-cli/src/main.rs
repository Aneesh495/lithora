//! Lithora command-line tool.
//!
//! Exposes the reconstruction core so a fresh reader can run a bounded demo
//! without any downloaded data: reconstruct a point, trace a motion path, or
//! report a present-day stage velocity from a rotation file. A built-in
//! synthetic model lets `lithora demo` run with no arguments.

use anyhow::{Context, Result};
use clap::{Parser, Subcommand};
use lithora_geo::coord::LatLon;
use lithora_geo::units::AgeMa;
use lithora_recon::Model;

/// A small synthetic two-plate model shipped for the zero-argument demo. It
/// is explicitly labelled synthetic and is not a published reconstruction.
const DEMO_ROT: &str = "\
# Synthetic demo model (NOT a published reconstruction)
801 0.0   0.0  0.0  0.0  701
801 50.0  30.0 40.0 8.0  701
801 100.0 30.0 40.0 16.0 701
701 0.0   0.0  0.0  0.0  0
701 50.0  10.0 -20.0 5.0 0
701 100.0 10.0 -20.0 10.0 0
";

#[derive(Parser)]
#[command(
    name = "lithora",
    version,
    about = "Tectonic reconstruction and kinematics core"
)]
struct Cli {
    #[command(subcommand)]
    command: Command,
}

#[derive(Subcommand)]
enum Command {
    /// Reconstruct a point to a geological age.
    Reconstruct {
        #[arg(long)]
        rot: Option<String>,
        #[arg(long, default_value_t = 0)]
        anchor: i64,
        #[arg(long)]
        plate: i64,
        #[arg(long)]
        lat: f64,
        #[arg(long)]
        lon: f64,
        #[arg(long)]
        age: f64,
    },
    /// Report a present-day stage speed in mm/yr for a point on a plate.
    Velocity {
        #[arg(long)]
        rot: Option<String>,
        #[arg(long, default_value_t = 0)]
        anchor: i64,
        #[arg(long)]
        plate: i64,
        #[arg(long)]
        lat: f64,
        #[arg(long)]
        lon: f64,
        #[arg(long, default_value_t = 1.0)]
        dt: f64,
    },
    /// Compare two rotation models at matched ages, reporting disagreement.
    Compare {
        #[arg(long)]
        rot_a: String,
        #[arg(long)]
        rot_b: String,
        #[arg(long, default_value_t = 0)]
        anchor: i64,
        #[arg(long)]
        plate: i64,
        #[arg(long)]
        lat: f64,
        #[arg(long)]
        lon: f64,
        /// Comma-separated ages in Ma, e.g. 0,25,50,100.
        #[arg(long)]
        ages: String,
    },
    /// Emit a motion path (reconstructed positions over a set of ages) as JSON.
    MotionPath {
        #[arg(long)]
        rot: Option<String>,
        #[arg(long, default_value_t = 0)]
        anchor: i64,
        #[arg(long)]
        plate: i64,
        #[arg(long)]
        lat: f64,
        #[arg(long)]
        lon: f64,
        /// Start, end, and step ages in Ma, e.g. 0:100:10.
        #[arg(long, default_value = "0:100:10")]
        ages: String,
    },
    /// Run a bounded end-to-end demo on the built-in synthetic model.
    Demo,
}

fn load_model(rot: &Option<String>, anchor: i64) -> Result<Model> {
    match rot {
        Some(path) => {
            let text = std::fs::read_to_string(path)
                .with_context(|| format!("reading rotation file {path}"))?;
            Model::from_rot_text(path.clone(), anchor, &text)
                .map_err(|e| anyhow::anyhow!("parse error: {e}"))
        }
        None => Model::from_rot_text("synthetic-demo", anchor, DEMO_ROT)
            .map_err(|e| anyhow::anyhow!("parse error: {e}")),
    }
}

fn main() -> Result<()> {
    let cli = Cli::parse();
    match cli.command {
        Command::Reconstruct {
            rot,
            anchor,
            plate,
            lat,
            lon,
            age,
        } => {
            let model = load_model(&rot, anchor)?;
            let p = model
                .reconstruct_point(LatLon::new(lat, lon), plate, AgeMa(age))
                .map_err(|e| anyhow::anyhow!("{e}"))?;
            println!(
                "{}",
                serde_json::json!({
                    "model": model.name,
                    "plate": plate,
                    "age_ma": age,
                    "input": {"lat": lat, "lon": lon},
                    "reconstructed": {"lat": p.lat_deg, "lon": p.lon_deg},
                })
            );
        }
        Command::Velocity {
            rot,
            anchor,
            plate,
            lat,
            lon,
            dt,
        } => {
            let model = load_model(&rot, anchor)?;
            let speed = model
                .present_speed_mm_per_yr(LatLon::new(lat, lon), plate, dt)
                .map_err(|e| anyhow::anyhow!("{e}"))?;
            println!(
                "{}",
                serde_json::json!({
                    "model": model.name,
                    "plate": plate,
                    "point": {"lat": lat, "lon": lon},
                    "stage_dt_ma": dt,
                    "speed_mm_per_yr": speed,
                })
            );
        }
        Command::Compare {
            rot_a,
            rot_b,
            anchor,
            plate,
            lat,
            lon,
            ages,
        } => {
            let model_a = load_model(&Some(rot_a), anchor)?;
            let model_b = load_model(&Some(rot_b), anchor)?;
            let age_vals: Vec<AgeMa> = ages
                .split(',')
                .filter_map(|s| s.trim().parse::<f64>().ok())
                .map(AgeMa)
                .collect();
            let pts = lithora_recon::compare_point(
                &model_a,
                &model_b,
                LatLon::new(lat, lon),
                plate,
                &age_vals,
            );
            let summary = lithora_recon::summarize(&pts);
            let rows: Vec<serde_json::Value> = pts
                .iter()
                .map(|p| match p {
                    lithora_recon::ComparisonPoint::Compared {
                        age,
                        angular_diff_rad,
                        pos_a,
                        pos_b,
                    } => {
                        serde_json::json!({
                            "age_ma": age.0,
                            "angular_diff_rad": angular_diff_rad,
                            "angular_diff_deg": angular_diff_rad.to_degrees(),
                            "pos_a": {"lat": pos_a.lat_deg, "lon": pos_a.lon_deg},
                            "pos_b": {"lat": pos_b.lat_deg, "lon": pos_b.lon_deg},
                        })
                    }
                    lithora_recon::ComparisonPoint::Unavailable { age, reason } => {
                        serde_json::json!({"age_ma": age.0, "unavailable": reason})
                    }
                })
                .collect();
            println!(
                "{}",
                serde_json::json!({
                    "plate": plate,
                    "point": {"lat": lat, "lon": lon},
                    "n_compared": summary.n_compared,
                    "n_unavailable": summary.n_unavailable,
                    "max_angular_diff_deg": summary.max_angular_diff_rad.to_degrees(),
                    "mean_angular_diff_deg": summary.mean_angular_diff_rad.to_degrees(),
                    "points": rows,
                })
            );
        }
        Command::MotionPath {
            rot,
            anchor,
            plate,
            lat,
            lon,
            ages,
        } => {
            let model = load_model(&rot, anchor)?;
            let age_vals = parse_age_range(&ages)?;
            let path = model.motion_path(LatLon::new(lat, lon), plate, &age_vals);
            let positions: Vec<serde_json::Value> = path
                .positions
                .iter()
                .map(|(age, p)| {
                    serde_json::json!({"age_ma": age.0, "lat": p.lat_deg, "lon": p.lon_deg})
                })
                .collect();
            println!(
                "{}",
                serde_json::json!({
                    "model": model.name,
                    "plate": plate,
                    "input": {"lat": lat, "lon": lon},
                    "n_supported": path.positions.len(),
                    "n_unsupported": path.unsupported,
                    "positions": positions,
                })
            );
        }
        Command::Demo => run_demo()?,
    }
    Ok(())
}

/// Parse a `start:end:step` age range in Ma into a vector of ages.
fn parse_age_range(spec: &str) -> Result<Vec<AgeMa>> {
    let parts: Vec<f64> = spec
        .split(':')
        .map(|s| s.trim().parse::<f64>())
        .collect::<std::result::Result<_, _>>()
        .map_err(|_| anyhow::anyhow!("invalid age range '{spec}', expected start:end:step"))?;
    if parts.len() != 3 {
        return Err(anyhow::anyhow!(
            "age range must be start:end:step, got '{spec}'"
        ));
    }
    let (start, end, step) = (parts[0], parts[1], parts[2]);
    if step <= 0.0 {
        return Err(anyhow::anyhow!("age step must be positive"));
    }
    let mut ages = Vec::new();
    let mut a = start;
    while a <= end + 1e-9 {
        ages.push(AgeMa(a));
        a += step;
    }
    Ok(ages)
}

fn run_demo() -> Result<()> {
    let model = load_model(&None, 0)?;
    println!(
        "Lithora demo on synthetic model '{}' ({} links)",
        model.name,
        model.link_count()
    );
    let point = LatLon::new(12.0, 45.0);
    println!("Tracking a point on plate 801 at (12 N, 45 E):");
    for age in [0.0, 25.0, 50.0, 75.0, 100.0] {
        let p = model
            .reconstruct_point(point, 801, AgeMa(age))
            .map_err(|e| anyhow::anyhow!("{e}"))?;
        println!(
            "  {age:6.1} Ma -> ({:8.4} N, {:9.4} E)",
            p.lat_deg, p.lon_deg
        );
    }
    let speed = model
        .present_speed_mm_per_yr(point, 801, 1.0)
        .map_err(|e| anyhow::anyhow!("{e}"))?;
    println!("Present-day stage speed at the point: {speed:.2} mm/yr");
    println!("(Ages beyond 100 Ma are unsupported by this model and would error, by design.)");
    Ok(())
}
