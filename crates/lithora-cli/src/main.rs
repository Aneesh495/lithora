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
        Command::Demo => run_demo()?,
    }
    Ok(())
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
