use serde::Serialize;
use std::process::Command;
use std::time::{SystemTime, UNIX_EPOCH};

#[derive(Serialize)]
struct AuditEvent<'a> {
    timestamp: u64,
    trigger: &'static str,
    route: &'a str,
    tool: &'a str,
    tier: &'a str,
    decision: &'a str,
    duration_ms: u128,
}

pub fn record(route: &str, tool: &str, tier: &str, decision: &str, duration_ms: u128) {
    let timestamp = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map_or(0, |duration| duration.as_secs());
    let event = AuditEvent {
        timestamp,
        trigger: "text",
        route,
        tool,
        tier,
        decision,
        duration_ms,
    };
    if let Ok(payload) = serde_json::to_string(&event) {
        let _ = Command::new("logger")
            .args(["-t", "hero-audit", "--", &payload])
            .status();
    }
}
