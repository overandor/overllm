//! A from-scratch, fully deterministic PRNG (splitmix64) and an FNV-1a
//! accumulator used to fingerprint a run.
//!
//! This is the core of OverML's reproducibility story: the generator is pure
//! integer arithmetic with no OS entropy, no per-platform float rounding
//! differences, and no "legacy vs new generator" API split — the two things
//! that routinely make "the same seed" produce different numbers across
//! numpy versions or machines. Same seed, same OverML build, same numbers,
//! everywhere.

pub struct DeterministicRng {
    state: u64,
}

impl DeterministicRng {
    pub fn new(seed: u64) -> Self {
        DeterministicRng {
            state: seed.wrapping_add(0x9E3779B97F4A7C15),
        }
    }

    pub fn next_u64(&mut self) -> u64 {
        self.state = self.state.wrapping_add(0x9E3779B97F4A7C15);
        let mut z = self.state;
        z = (z ^ (z >> 30)).wrapping_mul(0xBF58476D1CE4E5B9);
        z = (z ^ (z >> 27)).wrapping_mul(0x94D049BB133111EB);
        z ^ (z >> 31)
    }

    /// Uniform float in [0, 1).
    pub fn next_f64(&mut self) -> f64 {
        (self.next_u64() >> 11) as f64 * (1.0 / ((1u64 << 53) as f64))
    }
}

/// Running FNV-1a 64-bit hash used as an execution fingerprint: every seed,
/// every random draw, and every `print` output is fed in, so two runs that
/// produce identical fingerprints are provably observationally identical.
pub struct Fnv1a(u64);

impl Fnv1a {
    pub fn new() -> Self {
        Fnv1a(0xcbf29ce484222325)
    }

    pub fn write(&mut self, bytes: &[u8]) {
        for &b in bytes {
            self.0 ^= b as u64;
            self.0 = self.0.wrapping_mul(0x100000001b3);
        }
    }

    pub fn write_u64(&mut self, v: u64) {
        self.write(&v.to_le_bytes());
    }

    pub fn write_f64(&mut self, v: f64) {
        self.write(&v.to_bits().to_le_bytes());
    }

    pub fn finish_hex(&self) -> String {
        format!("{:016x}", self.0)
    }
}

impl Default for Fnv1a {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn same_seed_same_sequence() {
        let mut a = DeterministicRng::new(42);
        let mut b = DeterministicRng::new(42);
        for _ in 0..100 {
            assert_eq!(a.next_u64(), b.next_u64());
        }
    }

    #[test]
    fn different_seed_diverges() {
        let mut a = DeterministicRng::new(1);
        let mut b = DeterministicRng::new(2);
        assert_ne!(a.next_u64(), b.next_u64());
    }

    #[test]
    fn floats_in_unit_range() {
        let mut r = DeterministicRng::new(7);
        for _ in 0..1000 {
            let f = r.next_f64();
            assert!((0.0..1.0).contains(&f));
        }
    }

    #[test]
    fn hash_changes_with_input() {
        let mut h1 = Fnv1a::new();
        h1.write(b"hello");
        let mut h2 = Fnv1a::new();
        h2.write(b"world");
        assert_ne!(h1.finish_hex(), h2.finish_hex());
    }
}
