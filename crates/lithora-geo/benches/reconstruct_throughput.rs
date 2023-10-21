//! A dependency-free throughput benchmark for the hot reconstruction paths.
//!
//! This is not a statistical micro-benchmark harness; it is a repeatable
//! measurement of how many rotations, compositions, and containment tests the
//! core performs per second, so performance regressions are visible and the
//! tiling budget can be reasoned about. Run with `cargo bench` (it is a
//! `#[bench]`-free plain binary invoked via the bench harness below) or
//! directly. Results are printed, not asserted, except for a loose floor that
//! catches a catastrophic regression.

use lithora_geo::coord::LatLon;
use lithora_geo::polygon::SphericalRing;
use lithora_geo::rotation::Rotation;
use lithora_geo::testutil::Rng;
use lithora_geo::vec3::Vec3;
use std::time::Instant;

fn bench<F: FnMut()>(name: &str, iters: usize, mut f: F) -> f64 {
    // Warm up.
    for _ in 0..(iters / 10).max(1) {
        f();
    }
    let start = Instant::now();
    for _ in 0..iters {
        f();
    }
    let elapsed = start.elapsed().as_secs_f64();
    let per_sec = iters as f64 / elapsed;
    println!("{name:40} {iters:>10} iters  {elapsed:8.4}s  {per_sec:>14.0}/s");
    per_sec
}

fn main() {
    println!("Lithora core throughput (release build recommended)\n");
    let mut rng = Rng::new(2024);

    // Rotation application.
    let q = Rotation::from_axis_angle(Vec3::new(0.2, 0.5, 0.8), 0.7);
    let v = rng.unit_vec();
    let apply = bench("rotation.apply", 5_000_000, || {
        std::hint::black_box(q.apply(std::hint::black_box(v)));
    });
    assert!(apply > 1e6, "rotation apply throughput collapsed");

    // Composition.
    let a = Rotation::from_euler_pole(LatLon::new(10.0, 20.0), 15.0);
    let b = Rotation::from_euler_pole(LatLon::new(-30.0, 100.0), 25.0);
    bench("rotation.then (compose)", 5_000_000, || {
        std::hint::black_box(std::hint::black_box(a).then(std::hint::black_box(b)));
    });

    // Polygon containment on a realistic quad ring.
    let ring = SphericalRing::from_latlon(&[
        LatLon::new(-10.0, -10.0),
        LatLon::new(-10.0, 10.0),
        LatLon::new(10.0, 10.0),
        LatLon::new(10.0, -10.0),
    ])
    .unwrap();
    let pt = LatLon::new(0.0, 0.0);
    let contain = bench("polygon.contains (4-vertex)", 2_000_000, || {
        std::hint::black_box(ring.contains(std::hint::black_box(pt)));
    });
    assert!(contain > 1e5, "containment throughput collapsed");

    println!("\nDone.");
}
