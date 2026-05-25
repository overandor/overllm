use reqwest;
use serde_json;
use std::time::Duration;

use crate::telemetry::TelemetryEvent;

pub struct Publisher {
    client: reqwest::Client,
    endpoint: String,
}

impl Publisher {
    pub fn new(endpoint: String) -> Self {
        let client = reqwest::Client::builder()
            .timeout(Duration::from_secs(5))
            .build()
            .unwrap_or_else(|_| reqwest::Client::new());
        Publisher { client, endpoint }
    }

    pub async fn send(&self, event: &TelemetryEvent) -> Result<(), reqwest::Error> {
        let body = serde_json::to_string(event).unwrap_or_default();
        self.client
            .post(&self.endpoint)
            .header("Content-Type", "application/json")
            .body(body)
            .send()
            .await?;
        Ok(())
    }

    pub async fn send_batch(&self, events: &[TelemetryEvent]) {
        for ev in events {
            if let Err(e) = self.send(ev).await {
                eprintln!("[Publisher] Failed to send event: {}", e);
            }
        }
    }
}
