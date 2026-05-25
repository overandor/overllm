use petgraph::graph::{DiGraph, NodeIndex};
use petgraph::algo::dijkstra;
use serde::{Deserialize, Serialize};
use std::collections::{HashMap, HashSet};
use std::hash::{Hash, Hasher};
use std::collections::hash_map::DefaultHasher;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DAGNode {
    pub id: String,
    pub embedding: Vec<f32>,
    pub node_type: String, // "token", "concept", "trading", "telemetry"
    pub metadata: HashMap<String, String>,
    pub timestamp: i64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DAGEdge {
    pub from: String,
    pub to: String,
    pub weight: f32,
    pub edge_type: String, // "causal", "semantic", "temporal", "correlation"
}

pub struct DAGVectorSearch {
    graph: DiGraph<DAGNode, f32>,
    node_map: HashMap<String, NodeIndex>,
    dimension: usize,
    embedding_cache: HashMap<String, Vec<f32>>,
}

impl DAGVectorSearch {
    pub fn new(dimension: usize) -> Self {
        DAGVectorSearch {
            graph: DiGraph::new(),
            node_map: HashMap::new(),
            dimension,
            embedding_cache: HashMap::new(),
        }
    }

    pub fn add_node(&mut self, node: DAGNode) -> Result<(), String> {
        if node.embedding.len() != self.dimension {
            return Err(format!("Embedding dimension mismatch: expected {}, got {}", 
                self.dimension, node.embedding.len()));
        }

        let node_idx = self.graph.add_node(node.clone());
        self.node_map.insert(node.id.clone(), node_idx);
        self.embedding_cache.insert(node.id.clone(), node.embedding);
        
        Ok(())
    }

    pub fn add_edge(&mut self, edge: DAGEdge) -> Result<(), String> {
        let from_idx = self.node_map.get(&edge.from)
            .ok_or_else(|| format!("Source node {} not found", edge.from))?;
        let to_idx = self.node_map.get(&edge.to)
            .ok_or_else(|| format!("Target node {} not found", edge.to))?;

        self.graph.update_edge(*from_idx, *to_idx, edge.weight);
        Ok(())
    }

    pub fn vector_search(&self, query: &[f32], k: usize, node_type_filter: Option<&str>) -> Vec<(String, f32)> {
        if query.len() != self.dimension {
            return vec![];
        }

        let mut similarities: Vec<(String, f32)> = self.graph.node_indices()
            .filter_map(|idx| {
                let node = self.graph.node_weight(idx)?;
                if let Some(filter) = node_type_filter {
                    if node.node_type != filter {
                        return None;
                    }
                }
                let sim = cosine_similarity(query, &node.embedding);
                Some((node.id.clone(), sim))
            })
            .collect();

        similarities.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal));
        similarities.truncate(k);
        similarities
    }

    pub fn dag_search(&self, start_node: &str, end_node: &str) -> Option<Vec<String>> {
        let start_idx = self.node_map.get(start_node)?;
        let end_idx = self.node_map.get(end_node)?;

        let path = diijkstra(&self.graph, *start_idx, Some(*end_idx), 
            |e| *e.weight())?;

        Some(path.1.into_iter()
            .filter_map(|idx| self.graph.node_weight(idx).map(|n| n.id.clone()))
            .collect())
    }

    pub fn contextual_search(&self, query: &[f32], context_nodes: &[String], k: usize) -> Vec<(String, f32)> {
        // First, get initial vector search results
        let mut results = self.vector_search(query, k * 2, None);

        // Then, boost scores for nodes connected to context
        let context_set: HashSet<String> = context_nodes.iter().cloned().collect();
        
        for (node_id, score) in results.iter_mut() {
            if let Some(node_idx) = self.node_map.get(node_id) {
                // Check neighbors
                for neighbor in self.graph.neighbors(*node_idx) {
                    if let Some(neighbor_node) = self.graph.node_weight(neighbor) {
                        if context_set.contains(&neighbor_node.id) {
                            *score *= 1.5f32; // Boost score
                        }
                    }
                }
            }
        }

        results.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal));
        results.truncate(k);
        results
    }

    pub fn get_neighbors(&self, node_id: &str) -> Vec<String> {
        if let Some(node_idx) = self.node_map.get(node_id) {
            self.graph.neighbors(*node_idx)
                .filter_map(|idx| self.graph.node_weight(idx).map(|n| n.id.clone()))
                .collect()
        } else {
            vec![]
        }
    }

    pub fn get_node(&self, node_id: &str) -> Option<&DAGNode> {
        self.node_map.get(node_id)
            .and_then(|idx| self.graph.node_weight(*idx))
    }

    pub fn build_trading_dag(&mut self, candle_data: &Vec<CandleData>) {
        // Build DAG from trading candle data
        for (i, candle) in candle_data.iter().enumerate() {
            let embedding = self.embed_candle(candle);
            
            let node = DAGNode {
                id: format!("candle_{}_{}", candle.timestamp, i),
                embedding,
                node_type: "trading".to_string(),
                metadata: {
                    let mut meta = HashMap::new();
                    meta.insert("open".to_string(), candle.open.to_string());
                    meta.insert("high".to_string(), candle.high.to_string());
                    meta.insert("low".to_string(), candle.low.to_string());
                    meta.insert("close".to_string(), candle.close.to_string());
                    meta.insert("volume".to_string(), candle.volume.to_string());
                    meta.insert("interval".to_string(), candle.interval.clone());
                    meta
                },
                timestamp: candle.timestamp,
            };

            let _ = self.add_node(node);

            // Add temporal edges to previous candles
            if i > 0 {
                let prev_id = format!("candle_{}_{}", candle_data[i-1].timestamp, i-1);
                let curr_id = format!("candle_{}_{}", candle.timestamp, i);
                let edge = DAGEdge {
                    from: prev_id,
                    to: curr_id,
                    weight: 0.9,
                    edge_type: "temporal".to_string(),
                };
                let _ = self.add_edge(edge);
            }
        }
    }

    fn embed_candle(&self, candle: &CandleData) -> Vec<f32> {
        // Simple embedding based on candle features
        let mut embedding = vec![0.0f32; self.dimension];
        
        // Normalize and embed OHLCV
        let features = vec![
            candle.open, candle.high, candle.low, candle.close, candle.volume
        ];
        
        for (i, &feat) in features.iter().enumerate() {
            let idx = i % self.dimension;
            embedding[idx] = (feat.abs() as f32).ln_1p() / 10.0f32;
        }
        
        // Add temporal encoding
        let time_hash = self.hash_timestamp(candle.timestamp);
        for i in 0..self.dimension {
            embedding[i] += ((time_hash >> (i % 32)) & 1) as f32 * 0.1f32;
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

    fn hash_timestamp(&self, timestamp: i64) -> u64 {
        let mut hasher = DefaultHasher::new();
        timestamp.hash(&mut hasher);
        hasher.finish()
    }

    pub fn find_similar_patterns(&self, query_candle: &CandleData, k: usize) -> Vec<(String, f32)> {
        let query_embedding = self.embed_candle(query_candle);
        self.vector_search(&query_embedding, k, Some("trading"))
    }

    pub fn get_graph_stats(&self) -> (usize, usize) {
        (self.graph.node_count(), self.graph.edge_count())
    }
}

#[derive(Debug, Clone)]
pub struct CandleData {
    pub timestamp: i64,
    pub open: f64,
    pub high: f64,
    pub low: f64,
    pub close: f64,
    pub volume: f64,
    pub interval: String, // "1s", "1m", etc.
}

fn cosine_similarity(a: &[f32], b: &[f32]) -> f32 {
    if a.len() != b.len() || a.is_empty() {
        return 0.0f32;
    }

    let dot_product: f32 = a.iter().zip(b.iter()).map(|(x, y)| x * y).sum();
    let norm_a: f32 = a.iter().map(|x| x * x).sum::<f32>().sqrt();
    let norm_b: f32 = b.iter().map(|x| x * x).sum::<f32>().sqrt();

    if norm_a == 0.0 || norm_b == 0.0 {
        return 0.0f32;
    }

    dot_product / (norm_a * norm_b)
}
