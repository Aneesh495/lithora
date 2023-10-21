//! Bounded reconstruction cache with provenance-complete keys (L31, L32).
//!
//! Reconstructing a tile of geometry at an age is expensive enough to cache,
//! but a cache is dangerous if its keys are incomplete: returning a tile
//! computed for a different model, reference frame, time, or resolution is a
//! silent correctness bug. The cache key here includes every input that
//! changes the result, so a hit is guaranteed to be the right answer for the
//! exact request.
//!
//! The cache is bounded (least-recently-used eviction) so a long mixed-query
//! session stays within a memory budget, which is the resource behaviour gate
//! G12 cares about. It also carries a monotonically increasing generation
//! counter so an asynchronous consumer can discard results computed for a
//! superseded request: a slow reconstruction for an old time selection must
//! not overwrite a newer one.

use std::collections::HashMap;

/// A cache key that captures every input affecting a reconstructed tile.
/// Missing any of these would let a stale or wrong tile be returned.
#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub struct TileKey {
    /// Rotation model identity (name plus version).
    pub model: String,
    /// Reference frame label (e.g. the anchor plate or frame code).
    pub frame: String,
    /// Reconstruction age in whole thousands of years, to make the key
    /// hashable without floating-point ambiguity. Callers quantise the age.
    pub age_kyr: i64,
    /// Tile resolution level.
    pub resolution: u32,
    /// Tile column and row at that resolution.
    pub col: u32,
    pub row: u32,
    /// Inference checkpoint identity, empty when no learned layer is applied.
    pub checkpoint: String,
}

impl TileKey {
    /// Build a key, quantising a floating age in Ma to whole kyr.
    #[allow(clippy::too_many_arguments)]
    pub fn new(
        model: impl Into<String>,
        frame: impl Into<String>,
        age_ma: f64,
        resolution: u32,
        col: u32,
        row: u32,
        checkpoint: impl Into<String>,
    ) -> Self {
        TileKey {
            model: model.into(),
            frame: frame.into(),
            age_kyr: (age_ma * 1000.0).round() as i64,
            resolution,
            col,
            row,
            checkpoint: checkpoint.into(),
        }
    }
}

/// A bounded LRU cache from [`TileKey`] to a value. Eviction keeps the memory
/// footprint under the configured capacity.
pub struct TileCache<V> {
    capacity: usize,
    map: HashMap<TileKey, (u64, V)>, // value tagged with last-use tick
    tick: u64,
    generation: u64,
}

impl<V> TileCache<V> {
    pub fn new(capacity: usize) -> Self {
        assert!(capacity > 0, "cache capacity must be positive");
        TileCache {
            capacity,
            map: HashMap::new(),
            tick: 0,
            generation: 0,
        }
    }

    pub fn len(&self) -> usize {
        self.map.len()
    }

    pub fn is_empty(&self) -> bool {
        self.map.is_empty()
    }

    /// The current generation. Bump it with [`Self::new_generation`] when a
    /// new time/frame/model selection supersedes in-flight work.
    pub fn generation(&self) -> u64 {
        self.generation
    }

    /// Start a new generation and return its id. A consumer holding an older
    /// generation id should discard its result rather than insert it.
    pub fn new_generation(&mut self) -> u64 {
        self.generation += 1;
        self.generation
    }

    /// Whether a generation id is still current (not superseded).
    pub fn is_current(&self, gen: u64) -> bool {
        gen == self.generation
    }

    /// Look up a key, updating its recency on a hit.
    pub fn get(&mut self, key: &TileKey) -> Option<&V> {
        self.tick += 1;
        let tick = self.tick;
        if let Some(entry) = self.map.get_mut(key) {
            entry.0 = tick;
            Some(&entry.1)
        } else {
            None
        }
    }

    /// Insert a value, evicting the least recently used entry if at capacity.
    /// The insert is tagged with the generation guard: a stale generation is
    /// refused so a superseded computation cannot pollute the cache.
    pub fn insert_if_current(&mut self, gen: u64, key: TileKey, value: V) -> bool {
        if gen != self.generation {
            return false;
        }
        self.tick += 1;
        if !self.map.contains_key(&key) && self.map.len() >= self.capacity {
            self.evict_lru();
        }
        self.map.insert(key, (self.tick, value));
        true
    }

    fn evict_lru(&mut self) {
        if let Some(lru_key) = self
            .map
            .iter()
            .min_by_key(|(_, (t, _))| *t)
            .map(|(k, _)| k.clone())
        {
            self.map.remove(&lru_key);
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn key(age: f64, col: u32) -> TileKey {
        TileKey::new("EB-M7:v1", "anchor-0", age, 3, col, 0, "")
    }

    #[test]
    fn hit_and_miss() {
        let mut c: TileCache<i32> = TileCache::new(4);
        let g = c.generation();
        assert!(c.insert_if_current(g, key(10.0, 0), 42));
        assert_eq!(c.get(&key(10.0, 0)), Some(&42));
        assert_eq!(c.get(&key(20.0, 0)), None);
    }

    #[test]
    fn different_age_is_a_different_key() {
        let mut c: TileCache<i32> = TileCache::new(4);
        let g = c.generation();
        c.insert_if_current(g, key(10.0, 0), 1);
        c.insert_if_current(g, key(10.001, 0), 2); // +1 kyr -> distinct
        assert_eq!(c.get(&key(10.0, 0)), Some(&1));
        assert_eq!(c.get(&key(10.001, 0)), Some(&2));
    }

    #[test]
    fn model_frame_checkpoint_are_part_of_key() {
        let a = TileKey::new("modelA", "f1", 5.0, 2, 0, 0, "ckptX");
        let b = TileKey::new("modelB", "f1", 5.0, 2, 0, 0, "ckptX");
        let c = TileKey::new("modelA", "f2", 5.0, 2, 0, 0, "ckptX");
        let d = TileKey::new("modelA", "f1", 5.0, 2, 0, 0, "ckptY");
        assert_ne!(a, b);
        assert_ne!(a, c);
        assert_ne!(a, d);
    }

    #[test]
    fn lru_eviction_keeps_capacity() {
        let mut c: TileCache<i32> = TileCache::new(2);
        let g = c.generation();
        c.insert_if_current(g, key(1.0, 0), 1);
        c.insert_if_current(g, key(2.0, 1), 2);
        // Touch key 1 so it is more recently used than key 2.
        let _ = c.get(&key(1.0, 0));
        c.insert_if_current(g, key(3.0, 2), 3); // should evict key 2
        assert_eq!(c.len(), 2);
        assert_eq!(c.get(&key(2.0, 1)), None, "LRU entry should be evicted");
        assert_eq!(c.get(&key(1.0, 0)), Some(&1));
        assert_eq!(c.get(&key(3.0, 2)), Some(&3));
    }

    #[test]
    fn stale_generation_insert_is_refused() {
        let mut c: TileCache<i32> = TileCache::new(4);
        let old = c.generation();
        let new = c.new_generation();
        assert!(!c.is_current(old));
        assert!(c.is_current(new));
        // A result computed under the old generation must not be inserted.
        assert!(!c.insert_if_current(old, key(10.0, 0), 99));
        assert_eq!(c.get(&key(10.0, 0)), None);
        // The current generation inserts fine.
        assert!(c.insert_if_current(new, key(10.0, 0), 100));
        assert_eq!(c.get(&key(10.0, 0)), Some(&100));
    }
}
