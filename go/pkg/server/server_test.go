package server

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"github.com/overllm/overllm-agent/pkg/agent"
)

func newTestServer(t *testing.T, adminToken string) *Server {
	t.Helper()
	t.Setenv("HOME", t.TempDir())
	a := agent.NewAgent()
	return &Server{Agent: a, AdminToken: adminToken}
}

// TestOverAgentKeys_NoAdminTokenConfiguredFailsClosed locks in the fix for a
// real vulnerability: /api/overagent/keys used to have no authentication at
// all, so any caller could GET every issued API key's raw secret or POST to
// mint unlimited new ones. The fixed behavior must fail closed — with no
// OVERLLM_ADMIN_TOKEN configured, the endpoint is unavailable, not open.
func TestOverAgentKeys_NoAdminTokenConfiguredFailsClosed(t *testing.T) {
	s := newTestServer(t, "")
	req := httptest.NewRequest(http.MethodGet, "/api/overagent/keys", nil)
	w := httptest.NewRecorder()
	s.handleOverAgentKeys(w, req)
	if w.Code != http.StatusServiceUnavailable {
		t.Fatalf("expected 503 when no admin token is configured, got %d: %s", w.Code, w.Body.String())
	}
}

func TestOverAgentKeys_WrongTokenIsUnauthorized(t *testing.T) {
	s := newTestServer(t, "correct-token")
	req := httptest.NewRequest(http.MethodGet, "/api/overagent/keys", nil)
	req.Header.Set("Authorization", "Bearer wrong-token")
	w := httptest.NewRecorder()
	s.handleOverAgentKeys(w, req)
	if w.Code != http.StatusUnauthorized {
		t.Fatalf("expected 401 for a wrong token, got %d: %s", w.Code, w.Body.String())
	}
}

func TestOverAgentKeys_MissingTokenIsUnauthorized(t *testing.T) {
	s := newTestServer(t, "correct-token")
	req := httptest.NewRequest(http.MethodGet, "/api/overagent/keys", nil)
	w := httptest.NewRecorder()
	s.handleOverAgentKeys(w, req)
	if w.Code != http.StatusUnauthorized {
		t.Fatalf("expected 401 with no Authorization header, got %d: %s", w.Code, w.Body.String())
	}
}

func TestOverAgentKeys_CorrectTokenListsMaskedKeys(t *testing.T) {
	s := newTestServer(t, "correct-token")

	// Issue a key first so there's something to list.
	postBody, err := json.Marshal(map[string]interface{}{"owner": "test-owner"})
	if err != nil {
		t.Fatal(err)
	}
	postReq := httptest.NewRequest(http.MethodPost, "/api/overagent/keys", bytes.NewReader(postBody))
	postReq.Header.Set("Authorization", "Bearer correct-token")
	postW := httptest.NewRecorder()
	s.handleOverAgentKeys(postW, postReq)
	if postW.Code != http.StatusOK {
		t.Fatalf("expected 200 issuing a key, got %d: %s", postW.Code, postW.Body.String())
	}
	var issued struct {
		Key string `json:"key"`
	}
	if err := json.Unmarshal(postW.Body.Bytes(), &issued); err != nil {
		t.Fatalf("decode issue response: %v", err)
	}
	if issued.Key == "" {
		t.Fatal("expected the POST response to include the full raw key exactly once")
	}

	getReq := httptest.NewRequest(http.MethodGet, "/api/overagent/keys", nil)
	getReq.Header.Set("Authorization", "Bearer correct-token")
	getW := httptest.NewRecorder()
	s.handleOverAgentKeys(getW, getReq)
	if getW.Code != http.StatusOK {
		t.Fatalf("expected 200 listing keys, got %d: %s", getW.Code, getW.Body.String())
	}
	if body := getW.Body.String(); strings.Contains(body, issued.Key) {
		t.Fatalf("expected the listing to mask the raw key, but the full secret %q appeared in: %s", issued.Key, body)
	}
}

func TestMaskKey(t *testing.T) {
	got := maskKey("ovllm_0123456789abcdef")
	if strings.Contains(got, "0123456789abcdef") {
		t.Fatalf("maskKey leaked the full key: %q", got)
	}
	if !strings.HasPrefix(got, "ovllm_012") {
		t.Fatalf("expected a recognizable prefix for operators to match against logs, got %q", got)
	}
}
