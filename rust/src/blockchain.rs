use alloy::providers::{Provider, ProviderBuilder, ReqwestProvider};
use alloy::primitives::{Address, Bytes, FixedBytes, U256};
use alloy::rpc::types::eth::{Block, Transaction};
use serde::{Deserialize, Serialize};
use std::str::FromStr;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BlockchainEvent {
    pub chain_id: u64,
    pub block_number: u64,
    pub tx_hash: String,
    pub from_address: String,
    pub to_address: Option<String>,
    pub value: String,
    pub data: String,
    pub event_type: String, // "transfer", "swap", "mint", "burn", "contract_call"
    pub timestamp: i64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TokenPrice {
    pub symbol: String,
    pub address: String,
    pub price_usd: f64,
    pub change_24h: f64,
    pub volume_24h: f64,
}

pub struct BlockchainClient {
    provider: Option<ReqwestProvider>,
    chain_id: u64,
    rpc_url: String,
}

impl BlockchainClient {
    pub fn new(rpc_url: String, chain_id: u64) -> Self {
        let provider = ProviderBuilder::new()
            .on_http(rpc_url.parse().unwrap_or_else(|_| "http://localhost:8545".parse().unwrap()));
        
        BlockchainClient {
            provider: Some(provider),
            chain_id,
            rpc_url,
        }
    }

    pub async fn get_latest_block(&self) -> Result<Block, String> {
        if let Some(ref provider) = self.provider {
            provider.get_block_by_number(alloy::rpc::types::BlockNumberOrTag::Latest, false)
                .await
                .map_err(|e| format!("Failed to get block: {}", e))?
                .ok_or_else(|| "Block not found".to_string())
        } else {
            Err("Provider not initialized".to_string())
        }
    }

    pub async fn get_transaction(&self, tx_hash: &str) -> Result<Transaction, String> {
        if let Some(ref provider) = self.provider {
            let hash = FixedBytes::from_str(tx_hash)
                .map_err(|_| format!("Invalid tx hash: {}", tx_hash))?;
            
            provider.get_transaction_by_hash(hash)
                .await
                .map_err(|e| format!("Failed to get transaction: {}", e))?
                .ok_or_else(|| "Transaction not found".to_string())
        } else {
            Err("Provider not initialized".to_string())
        }
    }

    pub async fn get_balance(&self, address: &str) -> Result<U256, String> {
        if let Some(ref provider) = self.provider {
            let addr = Address::from_str(address)
                .map_err(|_| format!("Invalid address: {}", address))?;
            
            provider.get_balance(addr).await
                .map_err(|e| format!("Failed to get balance: {}", e))
        } else {
            Err("Provider not initialized".to_string())
        }
    }

    pub async fn watch_address(&self, address: &str) -> Vec<BlockchainEvent> {
        let mut events = Vec::new();
        
        // Get recent blocks and scan for transactions involving this address
        if let Ok(latest_block) = self.get_latest_block().await {
            let start_block = latest_block.header.number.saturating_sub(10);
            
            for block_num in start_block..=latest_block.header.number {
                if let Ok(block) = self.provider.as_ref()
                    .unwrap()
                    .get_block_by_number(block_num.into(), true)
                    .await
                {
                    if let Some(block) = block {
                        // Use hashes to get transaction hashes, then fetch each transaction
                        for tx_hash in block.transactions.hashes() {
                            if let Ok(tx) = self.get_transaction(&format!("{:?}", tx_hash)).await {
                                let from_addr = format!("{:?}", tx.from);
                                let to_addr = tx.to.map(|t| format!("{:?}", t));

                                if from_addr == address || to_addr.as_ref().map_or(false, |t| t == address) {
                                    events.push(BlockchainEvent {
                                        chain_id: self.chain_id,
                                        block_number: block_num,
                                        tx_hash: format!("{:?}", tx.hash),
                                        from_address: from_addr,
                                        to_address: to_addr,
                                        value: tx.value.to_string(),
                                        data: tx.input.to_string(),
                                        event_type: "transfer".to_string(),
                                        timestamp: chrono::Utc::now().timestamp(),
                                    });
                                }
                            }
                        }
                    }
                }
            }
        }
        
        events
    }

    pub async fn analyze_defi(&self, protocol: &str) -> Result<serde_json::Value, String> {
        // Analyze DeFi protocol positions (v1: mock data)
        // In production, use subgraph queries or protocol-specific APIs
        let analysis = serde_json::json!({
            "protocol": protocol,
            "total_value_locked": "1000000.0",
            "positions": [
                {
                    "pool": "ETH/USDC",
                    "position": "1000 ETH",
                    "value_usd": 2000000.0,
                    "pnl_24h": 5000.0,
                }
            ],
            "opportunities": [
                "Arbitrage opportunity detected between DEX A and DEX B",
                "Liquidity provision opportunity in pool X",
            ]
        });
        Ok(analysis)
    }

    pub async fn get_token_prices(&self, tokens: &[&str]) -> Vec<TokenPrice> {
        // v1: mock prices
        tokens.iter().map(|&symbol| TokenPrice {
            symbol: symbol.to_string(),
            address: format!("0x{}", hex::encode(symbol.as_bytes())),
            price_usd: rand::random::<f64>() * 1000.0,
            change_24h: (rand::random::<f64>() - 0.5) * 20.0,
            volume_24h: rand::random::<f64>() * 1000000.0,
        }).collect()
    }
}

// NFT metadata and analysis
pub struct NFTAnalyzer {
    client: BlockchainClient,
}

impl NFTAnalyzer {
    pub fn new(client: BlockchainClient) -> Self {
        NFTAnalyzer { client }
    }

    pub async fn analyze_collection(&self, contract_address: &str) -> Result<serde_json::Value, String> {
        // Analyze NFT collection rarity, floor price, etc.
        let analysis = serde_json::json!({
            "contract": contract_address,
            "floor_price": "0.5 ETH",
            "total_supply": 10000,
            "owners": 3500,
            "rarity_distribution": {
                "common": 0.6,
                "rare": 0.3,
                "legendary": 0.1,
            }
        });
        Ok(analysis)
    }
}
