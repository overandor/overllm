use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::fs::{File, OpenOptions};
use std::io::{BufRead, BufReader, Write};
use std::path::Path;
use std::sync::{Arc, Mutex};
use tokio::sync::mpsc;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Candle {
    pub timestamp: i64,
    pub open: f64,
    pub high: f64,
    pub low: f64,
    pub close: f64,
    pub volume: f64,
    pub interval: String, // "1s", "1m"
}

#[derive(Debug, Clone)]
pub struct TradingDataStore {
    candles_1s: Arc<Mutex<Vec<Candle>>>,
    candles_1m: Arc<Mutex<Vec<Candle>>>,
    current_1s: Arc<Mutex<Option<Candle>>>,
    current_1m: Arc<Mutex<Option<Candle>>>,
    max_candles: usize,
}

impl TradingDataStore {
    pub fn new(max_candles: usize) -> Self {
        TradingDataStore {
            candles_1s: Arc::new(Mutex::new(Vec::with_capacity(max_candles))),
            candles_1m: Arc::new(Mutex::new(Vec::with_capacity(max_candles))),
            current_1s: Arc::new(Mutex::new(None)),
            current_1m: Arc::new(Mutex::new(None)),
            max_candles,
        }
    }

    pub fn add_tick(&self, timestamp: i64, price: f64, volume: f64) {
        // Update 1-second candle
        {
            let mut current = self.current_1s.lock().unwrap();
            let interval_start = (timestamp / 1000) * 1000; // Round to second
            
            if current.is_none() || current.as_ref().unwrap().timestamp != interval_start {
                // Finalize previous candle
                if let Some(candle) = current.take() {
                    let mut candles = self.candles_1s.lock().unwrap();
                    candles.push(candle);
                    if candles.len() > self.max_candles {
                        candles.remove(0);
                    }
                }
                
                // Start new candle
                *current = Some(Candle {
                    timestamp: interval_start,
                    open: price,
                    high: price,
                    low: price,
                    close: price,
                    volume,
                    interval: "1s".to_string(),
                });
            } else {
                // Update existing candle
                if let Some(candle) = current.as_mut() {
                    candle.high = candle.high.max(price);
                    candle.low = candle.low.min(price);
                    candle.close = price;
                    candle.volume += volume;
                }
            }
        }

        // Update 1-minute candle
        {
            let mut current = self.current_1m.lock().unwrap();
            let interval_start = (timestamp / 60000) * 60000; // Round to minute
            
            if current.is_none() || current.as_ref().unwrap().timestamp != interval_start {
                // Finalize previous candle
                if let Some(candle) = current.take() {
                    let mut candles = self.candles_1m.lock().unwrap();
                    candles.push(candle);
                    if candles.len() > self.max_candles {
                        candles.remove(0);
                    }
                }
                
                // Start new candle
                *current = Some(Candle {
                    timestamp: interval_start,
                    open: price,
                    high: price,
                    low: price,
                    close: price,
                    volume,
                    interval: "1m".to_string(),
                });
            } else {
                // Update existing candle
                if let Some(candle) = current.as_mut() {
                    candle.high = candle.high.max(price);
                    candle.low = candle.low.min(price);
                    candle.close = price;
                    candle.volume += volume;
                }
            }
        }
    }

    pub fn get_candles_1s(&self, count: usize) -> Vec<Candle> {
        let candles = self.candles_1s.lock().unwrap();
        let len = candles.len();
        if len == 0 {
            return vec![];
        }
        let start = len.saturating_sub(count);
        candles[start..].to_vec()
    }

    pub fn get_candles_1m(&self, count: usize) -> Vec<Candle> {
        let candles = self.candles_1m.lock().unwrap();
        let len = candles.len();
        if len == 0 {
            return vec![];
        }
        let start = len.saturating_sub(count);
        candles[start..].to_vec()
    }

    pub fn get_latest_candle_1s(&self) -> Option<Candle> {
        let current = self.current_1s.lock().unwrap();
        current.clone()
    }

    pub fn get_latest_candle_1m(&self) -> Option<Candle> {
        let current = self.current_1m.lock().unwrap();
        current.clone()
    }

    pub fn calculate_indicators(&self, interval: &str, period: usize) -> HashMap<String, f64> {
        let candles = if interval == "1s" {
            self.get_candles_1s(period)
        } else {
            self.get_candles_1m(period)
        };

        if candles.is_empty() {
            return HashMap::new();
        }

        let mut indicators = HashMap::new();

        // SMA
        let sum: f64 = candles.iter().map(|c| c.close).sum();
        indicators.insert(format!("sma_{}", period), sum / candles.len() as f64);

        // EMA
        let multiplier = 2.0 / (period as f64 + 1.0);
        let mut ema = candles[0].close;
        for candle in candles.iter().skip(1) {
            ema = (candle.close - ema) * multiplier + ema;
        }
        indicators.insert(format!("ema_{}", period), ema);

        // RSI
        if candles.len() >= period + 1 {
            let mut gains = vec![];
            let mut losses = vec![];
            
            for i in 1..candles.len() {
                let change = candles[i].close - candles[i-1].close;
                if change > 0.0 {
                    gains.push(change);
                    losses.push(0.0);
                } else {
                    gains.push(0.0);
                    losses.push(-change);
                }
            }
            
            let avg_gain: f64 = gains.iter().sum::<f64>() / gains.len() as f64;
            let avg_loss: f64 = losses.iter().sum::<f64>() / losses.len() as f64;
            
            if avg_loss > 0.0 {
                let rs = avg_gain / avg_loss;
                let rsi = 100.0 - (100.0 / (1.0 + rs));
                indicators.insert(format!("rsi_{}", period), rsi);
            }
        }

        // Volatility (standard deviation)
        let mean = sum / candles.len() as f64;
        let variance: f64 = candles.iter()
            .map(|c| (c.close - mean).powi(2))
            .sum::<f64>() / candles.len() as f64;
        indicators.insert("volatility".to_string(), variance.sqrt());

        indicators
    }

    pub fn save_to_file(&self, path: &str) -> std::io::Result<()> {
        let file = OpenOptions::new()
            .write(true)
            .create(true)
            .truncate(true)
            .open(path)?;
        
        let mut writer = std::io::BufWriter::new(file);
        
        // Write 1s candles
        let candles_1s = self.candles_1s.lock().unwrap();
        writeln!(writer, "# 1-second candles")?;
        for candle in candles_1s.iter() {
            writeln!(writer, "{},{},{},{},{},{},{}", 
                candle.timestamp, candle.open, candle.high, 
                candle.low, candle.close, candle.volume, candle.interval)?;
        }
        
        // Write 1m candles
        let candles_1m = self.candles_1m.lock().unwrap();
        writeln!(writer, "# 1-minute candles")?;
        for candle in candles_1m.iter() {
            writeln!(writer, "{},{},{},{},{},{},{}", 
                candle.timestamp, candle.open, candle.high, 
                candle.low, candle.close, candle.volume, candle.interval)?;
        }
        
        Ok(())
    }

    pub fn load_from_file(&self, path: &str) -> std::io::Result<()> {
        if !Path::new(path).exists() {
            return Ok(());
        }

        let file = File::open(path)?;
        let reader = BufReader::new(file);
        
        let mut candles_1s = self.candles_1s.lock().unwrap();
        let mut candles_1m = self.candles_1m.lock().unwrap();
        
        candles_1s.clear();
        candles_1m.clear();
        
        let mut current_interval = "1s".to_string();
        
        for line in reader.lines() {
            let line = line?;
            if line.starts_with('#') {
                if line.contains("1-minute") {
                    current_interval = "1m".to_string();
                } else if line.contains("1-second") {
                    current_interval = "1s".to_string();
                }
                continue;
            }
            
            let parts: Vec<&str> = line.split(',').collect();
            if parts.len() >= 7 {
                let candle = Candle {
                    timestamp: parts[0].parse().unwrap_or(0),
                    open: parts[1].parse().unwrap_or(0.0),
                    high: parts[2].parse().unwrap_or(0.0),
                    low: parts[3].parse().unwrap_or(0.0),
                    close: parts[4].parse().unwrap_or(0.0),
                    volume: parts[5].parse().unwrap_or(0.0),
                    interval: parts[6].to_string(),
                };
                
                if current_interval == "1s" {
                    candles_1s.push(candle);
                } else {
                    candles_1m.push(candle);
                }
            }
        }
        
        Ok(())
    }
}

pub struct TradingSimulator {
    store: Arc<TradingDataStore>,
    running: Arc<Mutex<bool>>,
}

impl TradingSimulator {
    pub fn new(store: Arc<TradingDataStore>) -> Self {
        TradingSimulator {
            store,
            running: Arc::new(Mutex::new(false)),
        }
    }

    pub async fn start_simulation(&self, duration_secs: u64) {
        let mut running = self.running.lock().unwrap();
        *running = true;
        drop(running);

        let store = Arc::clone(&self.store);
        let running_flag = Arc::clone(&self.running);

        tokio::spawn(async move {
            let mut tick_count = 0u64;
            let start_time = std::time::Instant::now();
            
            while start_time.elapsed().as_secs() < duration_secs {
                {
                    let running = running_flag.lock().unwrap();
                    if !*running {
                        break;
                    }
                }

                // Simulate trading ticks
                let timestamp = Utc::now().timestamp_millis();
                let base_price = 50000.0 + (tick_count as f64 * 0.1);
                let noise = (rand::random::<f64>() - 0.5) * 100.0;
                let price = base_price + noise;
                let volume = rand::random::<f64>() * 10.0;
                
                store.add_tick(timestamp, price, volume);
                
                tick_count += 1;
                tokio::time::sleep(tokio::time::Duration::from_millis(100)).await;
            }
        });
    }

    pub fn stop_simulation(&self) {
        let mut running = self.running.lock().unwrap();
        *running = false;
    }
}
