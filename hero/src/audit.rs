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
    record_trigger("text", route, tool, tier, decision, duration_ms);
}

pub fn record_trigger(
    trigger: &'static str,
    route: &str,
    tool: &str,
    tier: &str,
    decision: &str,
    duration_ms: u128,
) {
    let timestamp = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map_or(0, |duration| duration.as_secs());
    if let Ok(payload) = event_json(trigger, route, tool, tier, decision, duration_ms, timestamp) {
        let _ = Command::new("logger")
            .args(["-t", "hero-audit", "--", &payload])
            .status();
    }
}

fn event_json(
    trigger: &'static str,
    route: &str,
    tool: &str,
    tier: &str,
    decision: &str,
    duration_ms: u128,
    timestamp: u64,
) -> Result<String, serde_json::Error> {
    let event = AuditEvent {
        timestamp,
        trigger,
        route,
        tool,
        tier,
        decision,
        duration_ms,
    };
    serde_json::to_string(&event)
}

#[cfg(test)]
mod tests {
    use super::event_json;

    #[test]
    fn audit_event_has_decision_metadata_and_no_query_field() {
        let json = event_json(
            "text",
            "código",
            "code.delegate",
            "alterar",
            "executado",
            42,
            123,
        )
        .expect("serialize event");
        let event: serde_json::Value = serde_json::from_str(&json).expect("event JSON");
        assert_eq!(event["timestamp"], 123);
        assert_eq!(event["trigger"], "text");
        assert_eq!(event["route"], "código");
        assert_eq!(event["tool"], "code.delegate");
        assert_eq!(event["tier"], "alterar");
        assert_eq!(event["decision"], "executado");
        assert_eq!(event["duration_ms"], 42);
        assert!(event.get("query").is_none());
    }
}
