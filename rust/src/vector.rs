use ndarray::{Array1, Array2};
use rand::Rng;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

// Simple HNSW wrapper since hnsw_rs may have API differences
struct SimpleHNSW {
    points: Vec<Vec<f32>>,
    ef_construction: usize,
}

impl SimpleHNSW {
    fn new(_dim: usize, ef_construction: usize, _max_elements: usize) -> Self {
        SimpleHNSW {
            points: Vec::new(),
            ef_construction,
        }
    }

    fn insert(&mut self, point: Vec<f32>, _idx: usize) {
        self.points.push(point);
    }

    fn search(&self, query: Vec<f32>, k: usize) -> Vec<(f64, usize)> {
        let mut results = Vec::new();
        for (i, p) in self.points.iter().enumerate() {
            let dist = cosine_distance(&query, p);
            results.push((dist, i));
        }
        results.sort_by(|a, b| a.0.partial_cmp(&b.0).unwrap());
        results.into_iter().take(k).collect()
    }
}

fn cosine_distance(a: &[f32], b: &[f32]) -> f64 {
    let mut dot = 0.0f64;
    let mut norm_a = 0.0f64;
    let mut norm_b = 0.0f64;
    for (x, y) in a.iter().zip(b.iter()) {
        dot += (*x as f64) * (*y as f64);
        norm_a += (*x as f64) * (*x as f64);
        norm_b += (*y as f64) * (*y as f64);
    }
    if norm_a == 0.0 || norm_b == 0.0 {
        return 1.0;
    }
    1.0 - dot / (norm_a.sqrt() * norm_b.sqrt())
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MemoryVector {
    pub id: String,
    pub embedding: Vec<f32>,
    pub metadata: HashMap<String, String>,
    pub timestamp: i64,
    pub source: String, // "telemetry", "blockchain", "article", "meta_llm"
}

pub struct VectorIndex {
    hnsw: SimpleHNSW,
    id_to_index: HashMap<String, usize>,
    vectors: Vec<MemoryVector>,
    dimension: usize,
}

impl VectorIndex {
    pub fn new(dimension: usize, ef_construction: usize, max_elements: usize) -> Self {
        let hnsw = SimpleHNSW::new(dimension, ef_construction, max_elements);
        VectorIndex {
            hnsw,
            id_to_index: HashMap::new(),
            vectors: Vec::new(),
            dimension,
        }
    }

    pub fn insert(&mut self, vector: MemoryVector) -> Result<(), String> {
        if vector.embedding.len() != self.dimension {
            return Err(format!("Embedding dimension mismatch: expected {}, got {}", 
                self.dimension, vector.embedding.len()));
        }
        
        let idx = self.vectors.len();
        self.id_to_index.insert(vector.id.clone(), idx);
        self.vectors.push(vector.clone());
        
        // Insert into HNSW
        let point: Vec<f32> = vector.embedding.clone();
        self.hnsw.insert(point, idx);
        
        Ok(())
    }

    pub fn search(&self, query: &[f32], k: usize) -> Vec<&MemoryVector> {
        if query.len() != self.dimension {
            return vec![];
        }
        
        let results = self.hnsw.search(query.to_vec(), k);
        results.iter()
            .filter_map(|(_, idx)| self.vectors.get(*idx))
            .collect()
    }

    pub fn get_by_id(&self, id: &str) -> Option<&MemoryVector> {
        self.id_to_index.get(id)
            .and_then(|idx| self.vectors.get(*idx))
    }

    pub fn delete(&mut self, id: &str) -> bool {
        if let Some(idx) = self.id_to_index.remove(id) {
            // HNSW doesn't support deletion easily, mark as deleted instead
            if let Some(vec) = self.vectors.get_mut(idx) {
                vec.metadata.insert("_deleted".to_string(), "true".to_string());
            }
            true
        } else {
            false
        }
    }

    pub fn len(&self) -> usize {
        self.vectors.len()
    }

    pub fn get_vectors_by_source(&self, source: &str) -> Vec<&MemoryVector> {
        self.vectors.iter()
            .filter(|v| v.source == source)
            .filter(|v| !v.metadata.contains_key("_deleted"))
            .collect()
    }
}

// Embedding generator using simple hash-based approach (v1)
// In production, use a real embedding model (e.g., sentence-transformers)
pub struct EmbeddingGenerator {
    dimension: usize,
}

impl EmbeddingGenerator {
    pub fn new(dimension: usize) -> Self {
        EmbeddingGenerator { dimension }
    }

    pub fn embed_text(&self, text: &str) -> Vec<f32> {
        let mut rng = rand::thread_rng();
        let mut embedding = vec![0.0f32; self.dimension];
        
        // Simple hash-based embedding (v1 - replace with real model)
        let bytes = text.as_bytes();
        for (i, &b) in bytes.iter().enumerate() {
            let idx = (i + b as usize) % self.dimension;
            embedding[idx] += (b as f32) / 255.0;
        }
        
        // Normalize
        let norm: f32 = embedding.iter().map(|x| x * x).sum::<f32>().sqrt();
        if norm > 0.0 {
            for v in embedding.iter_mut() {
                *v /= norm;
            }
        }
        
        embedding
    }

    pub fn embed_telemetry(&self, event_type: &str, data: &str) -> Vec<f32> {
        let text = format!("{}: {}", event_type, data);
        self.embed_text(&text)
    }

    pub fn embed_blockchain(&self, address: &str, tx_hash: &str, value: &str) -> Vec<f32> {
        let text = format!("blockchain: address={} tx={} value={}", address, tx_hash, value);
        self.embed_text(&text)
    }

    pub fn embed_article(&self, title: &str, abstract_text: &str) -> Vec<f32> {
        let text = format!("article: {} {}", title, abstract_text);
        self.embed_text(&text)
    }
}
