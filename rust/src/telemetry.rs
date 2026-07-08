use std::process::Command;
use std::time::{SystemTime, UNIX_EPOCH};
use std::sync::atomic::{AtomicBool, Ordering};

// Privacy controls. Telemetry is disabled by default and must be enabled by the
// daemon entrypoint, normally through OVERLLM_TELEMETRY=1.
static TELEMETRY_ENABLED: AtomicBool = AtomicBool::new(false);
static ANONYMIZE_DATA: AtomicBool = AtomicBool::new(true);

pub fn set_telemetry_enabled(enabled: bool) {
    TELEMETRY_ENABLED.store(enabled, Ordering::SeqCst);
}

pub fn set_anonymize_data(anonymize: bool) {
    ANONYMIZE_DATA.store(anonymize, Ordering::SeqCst);
}

fn is_telemetry_enabled() -> bool {
    TELEMETRY_ENABLED.load(Ordering::SeqCst)
}

fn should_anonymize() -> bool {
    ANONYMIZE_DATA.load(Ordering::SeqCst)
}

fn redact_sensitive(data: &str) -> String {
    if !should_anonymize() {
        return data.to_string();
    }

    // Redact file paths, usernames, and potentially sensitive strings.
    data
        .replace(&std::env::var("USER").unwrap_or_default(), "[USER]")
        .replace(&std::env::var("HOME").unwrap_or_default(), "[HOME]")
        .chars()
        .map(|c| if c.is_ascii_alphanumeric() || c == ' ' || c == '.' || c == '_' || c == '-' { c } else { '*' })
        .collect()
}

#[derive(Debug, Clone, serde::Serialize)]
pub struct TelemetryEvent {
    pub timestamp: i64,
    pub event_type: String,
    pub data: String,
    pub anonymized: bool,
}

pub fn get_active_app() -> Option<TelemetryEvent> {
    if !is_telemetry_enabled() {
        return None;
    }

    let script = r#"tell application "System Events" to get name of first application process whose frontmost is true"#;
    let output = Command::new("osascript")
        .args(["-e", script])
        .output()
        .ok()?;
    let name = String::from_utf8_lossy(&output.stdout).trim().to_string();
    if name.is_empty() {
        return None;
    }
    let redacted_name = redact_sensitive(&name);
    Some(TelemetryEvent {
        timestamp: now(),
        event_type: "active_app".to_string(),
        data: redacted_name,
        anonymized: should_anonymize(),
    })
}

pub fn get_system_stats() -> Option<TelemetryEvent> {
    if !is_telemetry_enabled() {
        return None;
    }

    let cpu = Command::new("sh")
        .args(["-c", "ps -A -o %cpu | awk '{s+=$1} END {print s}'"])
        .output()
        .ok()?;
    let mem = Command::new("sh")
        .args(["-c", "ps -A -o rss | awk '{s+=$1} END {print s/1024}'"])
        .output()
        .ok()?;
    let cpu_str = String::from_utf8_lossy(&cpu.stdout).trim().to_string();
    let mem_str = String::from_utf8_lossy(&mem.stdout).trim().to_string();
    Some(TelemetryEvent {
        timestamp: now(),
        event_type: "cpu_ram".to_string(),
        data: format!("cpu={}% ram={}MB", cpu_str, mem_str),
        anonymized: should_anonymize(),
    })
}

pub fn get_top_processes() -> Vec<TelemetryEvent> {
    if !is_telemetry_enabled() {
        return vec![];
    }
    let mut events = vec![];
    if let Ok(output) = Command::new("sh")
        .args(["-c", "ps -eo pid,pcpu,comm | sort -k2 -rn | head -n 5"])
        .output()
    {
        let text = String::from_utf8_lossy(&output.stdout);
        for line in text.lines().skip(1) {
            let parts: Vec<&str> = line.split_whitespace().collect();
            if parts.len() >= 3 {
                let process_name = redact_sensitive(parts[2]);
                events.push(TelemetryEvent {
                    timestamp: now(),
                    event_type: "process".to_string(),
                    data: format!("{} cpu={}%", process_name, parts[1]),
                    anonymized: should_anonymize(),
                });
            }
        }
    }
    events
}

pub fn get_recent_files() -> Vec<TelemetryEvent> {
    if !is_telemetry_enabled() {
        return vec![];
    }
    let mut events = vec![];
    if let Ok(output) = Command::new("lsof")
        .args(["-u", whoami().as_str(), "-F", "n"])
        .output()
    {
        let text = String::from_utf8_lossy(&output.stdout);
        let mut count = 0;
        for line in text.lines() {
            if line.starts_with('n') && count < 10 {
                let path = &line[1..];
                let redacted_path = redact_sensitive(path);
                events.push(TelemetryEvent {
                    timestamp: now(),
                    event_type: "file_access".to_string(),
                    data: redacted_path.to_string(),
                    anonymized: should_anonymize(),
                });
                count += 1;
            }
        }
    }
    events
}

pub fn get_network_summary() -> Option<TelemetryEvent> {
    if !is_telemetry_enabled() {
        return None;
    }
    if let Ok(output) = Command::new("netstat").args(["-an"]).output() {
        let text = String::from_utf8_lossy(&output.stdout);
        let established = text.lines().filter(|l| l.contains("ESTABLISHED")).count();
        let listen = text.lines().filter(|l| l.contains("LISTEN")).count();
        return Some(TelemetryEvent {
            timestamp: now(),
            event_type: "network".to_string(),
            data: format!("established={} listen={}", established, listen),
            anonymized: should_anonymize(),
        });
    }
    None
}

pub fn get_click_context() -> Option<TelemetryEvent> {
    get_active_app().map(|mut ev| {
        ev.event_type = "click".to_string();
        ev.data = format!("window_switch: {}", ev.data);
        ev
    })
}

fn now() -> i64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_secs() as i64
}

fn whoami() -> String {
    std::env::var("USER").unwrap_or_else(|_| "user".to_string())
}
