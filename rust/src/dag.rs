use petgraph::graph::{DiGraph, NodeIndex};
use petgraph::algo::toposort;
use petgraph::visit::{Dfs, EdgeRef};
use serde::{Deserialize, Serialize};
use std::collections::{HashMap, HashSet};
use std::time::{SystemTime, UNIX_EPOCH};

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum NodeType {
    Telemetry,
    Blockchain,
    Article,
    MetaLLM,
    Inference,
    Training,
    Reward,
    Punishment,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MemoryNode {
    pub id: String,
    pub node_type: NodeType,
    pub data: String,
    pub embedding: Vec<f32>,
    pub timestamp: i64,
    pub collateral_value: f64, // 0.0 to 1.0, higher = more valuable
    pub access_count: u64,
    pub last_accessed: i64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MemoryEdge {
    pub from: String,
    pub to: String,
    pub edge_type: String, // "causes", "relates_to", "improves", "punishes"
    pub weight: f64,
    pub timestamp: i64,
}

pub struct MemoryCollateralizer {
    graph: DiGraph<MemoryNode, MemoryEdge>,
    id_to_index: HashMap<String, NodeIndex>,
    root_nodes: Vec<String>,
    collateral_threshold: f64,
}

impl MemoryCollateralizer {
    pub fn new(collateral_threshold: f64) -> Self {
        MemoryCollateralizer {
            graph: DiGraph::new(),
            id_to_index: HashMap::new(),
            root_nodes: Vec::new(),
            collateral_threshold,
        }
    }

    pub fn add_node(&mut self, node: MemoryNode) -> NodeIndex {
        let idx = self.graph.add_node(node.clone());
        self.id_to_index.insert(node.id.clone(), idx);
        
        // If it's a root-level event (telemetry, blockchain), add to roots
        matches!(node.node_type, NodeType::Telemetry | NodeType::Blockchain | NodeType::Article)
            .then(|| self.root_nodes.push(node.id.clone()));
        
        idx
    }

    pub fn add_edge(&mut self, edge: MemoryEdge) -> Result<(), String> {
        let from_idx = self.id_to_index.get(&edge.from)
            .ok_or_else(|| format!("From node not found: {}", edge.from))?;
        let to_idx = self.id_to_index.get(&edge.to)
            .ok_or_else(|| format!("To node not found: {}", edge.to))?;
        
        self.graph.add_edge(*from_idx, *to_idx, edge);
        Ok(())
    }

    pub fn get_node(&self, id: &str) -> Option<&MemoryNode> {
        self.id_to_index.get(id)
            .and_then(|idx| self.graph.node_weight(*idx))
    }

    pub fn update_collateral(&mut self, id: &str, delta: f64) -> Result<(), String> {
        let idx = self.id_to_index.get(id)
            .ok_or_else(|| format!("Node not found: {}", id))?;
        
        if let Some(node) = self.graph.node_weight_mut(*idx) {
            node.collateral_value = (node.collateral_value + delta).clamp(0.0, 1.0);
            node.last_accessed = now();
            node.access_count += 1;
        }
        Ok(())
    }

    pub fn propagate_reward(&mut self, reward_node_id: &str, reward_amount: f64) {
        // Propagate reward backward through DAG to all ancestors
        if let Some(&idx) = self.id_to_index.get(reward_node_id) {
            let mut dfs = Dfs::new(&self.graph, idx);
            let mut visited = HashSet::new();
            
            while let Some(nx) = dfs.next(&self.graph) {
                if !visited.insert(nx) {
                    continue;
                }

                // Find incoming edges and propagate
                let sources: Vec<NodeIndex> = self.graph
                    .edges_directed(nx, petgraph::Direction::Incoming)
                    .filter_map(|edge| self.graph.edge_endpoints(edge.id()))
                    .map(|(source, _)| source)
                    .collect();

                for source in sources {
                    if let Some(node) = self.graph.node_weight_mut(source) {
                        let propagated = reward_amount * 0.5; // Fixed weight for now
                        node.collateral_value = (node.collateral_value + propagated).clamp(0.0, 1.0);
                        node.last_accessed = now();
                    }
                }
            }
        }
    }

    pub fn prune_low_collateral(&mut self) -> Vec<String> {
        let mut to_remove = Vec::new();
        
        for (id, idx) in &self.id_to_index {
            if let Some(node) = self.graph.node_weight(*idx) {
                if node.collateral_value < self.collateral_threshold 
                    && node.node_type != NodeType::Telemetry {
                    to_remove.push(id.clone());
                }
            }
        }
        
        for id in &to_remove {
            if let Some(idx) = self.id_to_index.remove(id) {
                self.graph.remove_node(idx);
            }
        }
        
        to_remove
    }

    pub fn get_high_collateral_chain(&self, start_id: &str, max_depth: usize) -> Vec<&MemoryNode> {
        let mut chain = Vec::new();
        let mut visited = HashSet::new();
        
        if let Some(&start_idx) = self.id_to_index.get(start_id) {
            self.collect_high_collateral(start_idx, max_depth, 0, &mut chain, &mut visited);
        }
        
        chain
    }

    fn collect_high_collateral<'a>(
        &'a self,
        idx: NodeIndex,
        max_depth: usize,
        current_depth: usize,
        chain: &mut Vec<&'a MemoryNode>,
        visited: &mut HashSet<NodeIndex>,
    ) {
        if current_depth >= max_depth || !visited.insert(idx) {
            return;
        }

        if let Some(node) = self.graph.node_weight(idx) {
            if node.collateral_value >= self.collateral_threshold {
                chain.push(node);

                // Follow outgoing edges
                for edge in self.graph.edges_directed(idx, petgraph::Direction::Outgoing) {
                    if let Some((_, target)) = self.graph.edge_endpoints(edge.id()) {
                        self.collect_high_collateral(target, max_depth, current_depth + 1, chain, visited);
                    }
                }
            }
        }
    }

    pub fn export_subgraph(&self, root_id: &str) -> Result<serde_json::Value, String> {
        let mut nodes = Vec::new();
        let mut edges = Vec::new();
        let mut visited = HashSet::new();
        
        if let Some(&root_idx) = self.id_to_index.get(root_id) {
            self.export_recursive(root_idx, &mut nodes, &mut edges, &mut visited);
        }
        
        Ok(serde_json::json!({
            "nodes": nodes,
            "edges": edges,
        }))
    }

    fn export_recursive(
        &self,
        idx: NodeIndex,
        nodes: &mut Vec<MemoryNode>,
        edges: &mut Vec<MemoryEdge>,
        visited: &mut HashSet<NodeIndex>,
    ) {
        if !visited.insert(idx) {
            return;
        }
        
        if let Some(node) = self.graph.node_weight(idx) {
            nodes.push(node.clone());
            
            for edge in self.graph.edges_directed(idx, petgraph::Direction::Outgoing) {
                if let Some((_, target)) = self.graph.edge_endpoints(edge.id()) {
                    edges.push(edge.weight().clone());
                    self.export_recursive(target, nodes, edges, visited);
                }
            }
        }
    }

    pub fn topological_sort(&self) -> Result<Vec<String>, String> {
        match toposort(&self.graph, None) {
            Ok(indices) => {
                let mut ids = Vec::new();
                for idx in indices {
                    if let Some(node) = self.graph.node_weight(idx) {
                        ids.push(node.id.clone());
                    }
                }
                Ok(ids)
            }
            Err(_) => Err("Cycle detected in memory DAG".to_string()),
        }
    }

    pub fn stats(&self) -> HashMap<String, String> {
        let mut stats = HashMap::new();
        stats.insert("total_nodes".to_string(), self.graph.node_count().to_string());
        stats.insert("total_edges".to_string(), self.graph.edge_count().to_string());
        stats.insert("root_nodes".to_string(), self.root_nodes.len().to_string());
        
        let high_collateral = self.graph.node_weights()
            .filter(|n| n.collateral_value >= self.collateral_threshold)
            .count();
        stats.insert("high_collateral_nodes".to_string(), high_collateral.to_string());
        
        stats
    }
}

fn now() -> i64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_secs() as i64
}
