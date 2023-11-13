//! Gate G12 (diagnostic): the bounded cache stays within its capacity under a
//! long mixed-query load, never returns a result for a different request, and
//! drops superseded-generation work.
//!
//! This is the laptop-sized diagnostic version of the resource-behaviour gate.
//! The full 12-hour mixed-query run is declared in the experiment plan; the
//! invariants it must preserve are exactly the ones checked here, at a scale
//! that runs in CI.

use lithora_recon::{TileCache, TileKey};

fn key(model: &str, frame: &str, age: f64, col: u32) -> TileKey {
    TileKey::new(model, frame, age, 4, col, 0, "")
}

#[test]
fn cache_stays_bounded_under_mixed_load() {
    let capacity = 256;
    let mut cache: TileCache<u64> = TileCache::new(capacity);
    let gen = cache.generation();

    // Simulate 200,000 mixed queries across models, frames, ages, and tiles.
    // A simple LCG drives the pseudo-random request stream deterministically.
    let mut lcg: u64 = 0x1234_5678;
    let models = ["EB-M7:v1", "EB-M9:v2"];
    let frames = ["anchor-0", "anchor-701"];
    let mut hits = 0u64;
    let mut inserts = 0u64;

    for _ in 0..200_000 {
        lcg = lcg
            .wrapping_mul(6364136223846793005)
            .wrapping_add(1442695040888963407);
        let model = models[(lcg >> 33) as usize % models.len()];
        let frame = frames[(lcg >> 17) as usize % frames.len()];
        let age = ((lcg >> 5) % 200) as f64; // 0..200 Ma
        let col = (lcg % 64) as u32;
        let k = key(model, frame, age, col);

        if cache.get(&k).is_some() {
            hits += 1;
        } else {
            let value = lcg; // stand-in for a computed tile
            assert!(cache.insert_if_current(gen, k, value));
            inserts += 1;
        }
        // The core invariant: the cache never exceeds its capacity.
        assert!(cache.len() <= capacity, "cache exceeded capacity");
    }

    // With a bounded cache and a large key space we expect some hits and many
    // inserts, and the final size must be exactly the capacity (it filled up).
    assert_eq!(cache.len(), capacity);
    assert!(inserts > 0 && hits > 0, "expected both hits and inserts");
}

#[test]
fn superseded_generation_results_are_dropped() {
    let mut cache: TileCache<u64> = TileCache::new(64);

    // A consumer starts work under the current generation.
    let work_gen = cache.generation();
    let k1 = key("EB-M7:v1", "anchor-0", 10.0, 0);

    // A newer time selection supersedes it.
    let _newer = cache.new_generation();

    // The stale result must be refused, keeping the cache free of answers for
    // a request the user already moved past.
    assert!(!cache.insert_if_current(work_gen, k1.clone(), 42));
    assert!(cache.get(&k1).is_none());

    // Work under the current generation inserts normally.
    let cur = cache.generation();
    assert!(cache.insert_if_current(cur, k1.clone(), 7));
    assert_eq!(cache.get(&k1), Some(&7));
}

#[test]
fn never_returns_a_tile_for_a_different_request() {
    let mut cache: TileCache<u64> = TileCache::new(16);
    let gen = cache.generation();
    cache.insert_if_current(gen, key("modelA", "f1", 10.0, 0), 111);
    // Any single differing component must miss.
    assert!(cache.get(&key("modelB", "f1", 10.0, 0)).is_none());
    assert!(cache.get(&key("modelA", "f2", 10.0, 0)).is_none());
    assert!(cache.get(&key("modelA", "f1", 11.0, 0)).is_none());
    assert!(cache.get(&key("modelA", "f1", 10.0, 1)).is_none());
    // Only the exact request hits.
    assert_eq!(cache.get(&key("modelA", "f1", 10.0, 0)), Some(&111));
}
