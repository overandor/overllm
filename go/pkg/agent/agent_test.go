package agent

import (
	"encoding/json"
	"strings"
	"testing"
)

// TestTelemetryEvent_DecodesRustWireFormat locks in the fix for a real
// integration bug: rust/src/telemetry.rs's TelemetryEvent always serializes
// its type field as "event_type" (no serde rename), but this struct used to
// declare `json:"type"`. json.Unmarshal silently leaves unmatched fields at
// their zero value instead of erroring, so every ingested event's Type
// silently became "" — telemetry could flow in all day and BuildContext's
// switch on ev.Type would never match any case.
func TestTelemetryEvent_DecodesRustWireFormat(t *testing.T) {
	// This is exactly the shape rust/src/telemetry.rs::TelemetryEvent
	// serializes to (see get_active_app, which sets event_type: "active_app").
	rustPayload := `{"timestamp":1700000000,"event_type":"active_app","data":"Terminal","anonymized":true}`

	var ev TelemetryEvent
	if err := json.Unmarshal([]byte(rustPayload), &ev); err != nil {
		t.Fatalf("unmarshal failed: %v", err)
	}
	if ev.Type != "active_app" {
		t.Fatalf("expected Type %q, got %q (Rust's event_type field didn't decode)", "active_app", ev.Type)
	}
	if ev.Data != "Terminal" {
		t.Fatalf("expected Data %q, got %q", "Terminal", ev.Data)
	}
}

func TestBuildContext_FormatsIngestedEvents(t *testing.T) {
	a := &Agent{
		Telemetry: []TelemetryEvent{
			{Timestamp: 1, Type: "active_app", Data: "Terminal"},
			{Timestamp: 2, Type: "cpu_ram", Data: "cpu=12% ram=340MB"},
			{Timestamp: 3, Type: "unknown_future_type", Data: "should be dropped, not crash"},
		},
	}
	ctx := a.BuildContext()
	if !strings.Contains(ctx, "Active app: Terminal") {
		t.Errorf("expected context to include the active app line, got: %q", ctx)
	}
	if !strings.Contains(ctx, "System: cpu=12% ram=340MB") {
		t.Errorf("expected context to include the system stats line, got: %q", ctx)
	}
}

func TestBuildContext_EmptyTelemetryIsEmptyContext(t *testing.T) {
	a := &Agent{}
	if ctx := a.BuildContext(); ctx != "" {
		t.Errorf("expected empty context for no telemetry, got: %q", ctx)
	}
}
