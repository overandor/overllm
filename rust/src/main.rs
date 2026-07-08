use tokio::time::{interval, Duration};
use overllm_telemetry::telemetry;
use overllm_telemetry::publisher::Publisher;
use overllm_telemetry::vector::{VectorIndex, EmbeddingGenerator, MemoryVector};
use overllm_telemetry::dag::{MemoryCollateralizer, MemoryNode, NodeType};
use overllm_telemetry::blockchain::BlockchainClient;
use overllm_telemetry::article::ArticleIngestor;
use overllm_telemetry::reinforcement::RLTrainer;
use std::collections::HashMap;
use std::sync::Arc;
use tokio::sync::Mutex;

#[tokio::main]
async fn main() {
    println!("=== OverLLM Enhanced Telemetry Daemon ===");
    println!("Modules: Vector Search | DAG Memory | Blockchain | Articles | RL");
    println!("Sending events to http://localhost:7749/telemetry");
    println!();

    // Telemetry (active app, processes, file access, network) is
    // privacy-sensitive and opt-in: previously nothing ever called
    // telemetry::set_telemetry_enabled, so the flag it gates on stayed at
    // its default (false) forever and those collectors silently returned
    // nothing no matter how long the daemon ran. Keep the safe default,
    // but make the state explicit and visible instead of silently inert.
    let telemetry_enabled = std::env::var("OVERLLM_TELEMETRY_ENABLED")
        .map(|v| v == "1" || v.eq_ignore_ascii_case("true"))
        .unwrap_or(false);
    telemetry::set_telemetry_enabled(telemetry_enabled);
    if telemetry_enabled {
        println!("[Telemetry] collection: ENABLED (active app, processes, file access, network)");
    } else {
        println!("[Telemetry] collection: DISABLED — set OVERLLM_TELEMETRY_ENABLED=1 to enable active-app/process/file/network capture");
    }
    println!();

    // Initialize new modules with Arc/Mutex for thread safety
    let vector_index = Arc::new(Mutex::new(VectorIndex::new(128, 32, 10000)));
    let embedder = Arc::new(EmbeddingGenerator::new(128));
    let dag = Arc::new(Mutex::new(MemoryCollateralizer::new(0.3)));
    let blockchain = Arc::new(BlockchainClient::new("http://localhost:8545".to_string(), 1));
    let article_ingestor = Arc::new(ArticleIngestor::new(128));
    
    // RL Trainer
    let rl_trainer = Arc::new(Mutex::new(RLTrainer::new(64, 10)));
    
    let publisher = Publisher::new("http://localhost:7749/telemetry".to_string());
    let mut tick = interval(Duration::from_secs(5));
    
    // DAG maintenance task
    let dag_maint = dag.clone();
    tokio::spawn(async move {
        let mut maintenance_tick = interval(Duration::from_secs(60));
        loop {
            maintenance_tick.tick().await;
            println!("[Maintenance] Pruning low collateral nodes...");
            let mut dag = dag_maint.lock().await;
            let removed = dag.prune_low_collateral();
            println!("[Maintenance] Removed {} low-value nodes", removed.len());
        }
    });
    
    // RL training loop
    let rl = rl_trainer.clone();
    tokio::spawn(async move {
        let mut rl_tick = interval(Duration::from_secs(30));
        loop {
            rl_tick.tick().await;
            let mut trainer = rl.lock().await;
            let rewards = trainer.train(5);
            println!("[RL] Training episode, avg reward: {:.2}", rewards.iter().sum::<f64>() / rewards.len() as f64);
        }
    });

    // Tracks time-since-last-run for the two periodic tasks below. These
    // used to be gated by `Instant::now().elapsed().as_secs() % N == 0`,
    // but that creates the Instant and immediately reads its elapsed time
    // in the same expression — elapsed() is always ~0 microseconds, so
    // `0 % N == 0` is always true and both tasks actually ran on every
    // 5-second tick instead of every 30s / 300s.
    let mut last_blockchain_check = tokio::time::Instant::now();
    let mut last_article_fetch = tokio::time::Instant::now();

    loop {
        tick.tick().await;

        let mut batch = vec![];

        // System telemetry
        if let Some(ev) = telemetry::get_active_app() {
            batch.push(ev.clone());
            
            // Add to vector index
            let embedding = embedder.embed_telemetry(&ev.event_type, &ev.data);
            let mut metadata = HashMap::new();
            metadata.insert("event_type".to_string(), ev.event_type.clone());
            let mem_vec = MemoryVector {
                id: format!("tel_{}", ev.timestamp),
                embedding,
                metadata,
                timestamp: ev.timestamp,
                source: "telemetry".to_string(),
            };
            let mut vi = vector_index.lock().await;
            let _ = vi.insert(mem_vec);
            
            // Add to DAG
            let node = MemoryNode {
                id: format!("tel_{}", ev.timestamp),
                node_type: NodeType::Telemetry,
                data: ev.data.clone(),
                embedding: embedder.embed_telemetry(&ev.event_type, &ev.data),
                timestamp: ev.timestamp,
                collateral_value: 0.5,
                access_count: 1,
                last_accessed: ev.timestamp,
            };
            let mut d = dag.lock().await;
            let _ = d.add_node(node);
        }
        
        if let Some(ev) = telemetry::get_system_stats() {
            batch.push(ev);
        }
        if let Some(ev) = telemetry::get_network_summary() {
            batch.push(ev);
        }
        if let Some(ev) = telemetry::get_click_context() {
            batch.push(ev);
        }

        batch.extend(telemetry::get_top_processes());
        batch.extend(telemetry::get_recent_files());

        if !batch.is_empty() {
            println!("[Telemetry] Sending {} events", batch.len());
            publisher.send_batch(&batch).await;
        }
        
        // Blockchain monitoring (every 30s)
        if last_blockchain_check.elapsed().as_secs() >= 30 {
            last_blockchain_check = tokio::time::Instant::now();
            let events = blockchain.watch_address("0x1234...").await;
            println!("[Blockchain] Found {} relevant transactions", events.len());
            for event in events {
                let embedding = embedder.embed_blockchain(&event.from_address, &event.tx_hash, &event.value);
                let mem_vec = MemoryVector {
                    id: event.tx_hash.clone(),
                    embedding,
                    metadata: HashMap::new(),
                    timestamp: event.timestamp,
                    source: "blockchain".to_string(),
                };
                let mut vi = vector_index.lock().await;
                let _ = vi.insert(mem_vec);
            }
        }
        
        // Article ingestion (every 5 minutes)
        if last_article_fetch.elapsed().as_secs() >= 300 {
            last_article_fetch = tokio::time::Instant::now();
            if let Ok(articles) = article_ingestor.fetch_arxiv("machine learning", 5).await {
                println!("[Articles] Ingested {} new research papers", articles.len());
                for article in articles {
                    let mem_vec = MemoryVector {
                        id: article.id.clone(),
                        embedding: article.embedding.clone(),
                        metadata: HashMap::new(),
                        timestamp: article.timestamp,
                        source: "article".to_string(),
                    };
                    let mut vi = vector_index.lock().await;
                    let _ = vi.insert(mem_vec);
                }
            }
        }
    }
}
