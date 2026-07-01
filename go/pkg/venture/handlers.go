package venture

import (
	"encoding/json"
	"net/http"
	"strings"
)

// Handlers exposes VentureChain deals and Breakthrough Verification Engine
// claims over HTTP, mirroring proof.Handlers. Deals and claims each have
// several sub-resources (artifacts, risk, approvals, evidence, firewall,
// ...); since net/http's default mux only does exact and subtree ("/foo/")
// matching, each subtree is registered once and dispatched here by path
// suffix, the same way proof.Handlers dispatches receipt IDs.
type Handlers struct {
	Deals  *Store
	Claims *ClaimStore
}

// NewHandlers creates Handlers backed by stores persisted under dataDir.
func NewHandlers(dataDir string) *Handlers {
	return &Handlers{
		Deals:  NewStore(dataDir),
		Claims: NewClaimStore(dataDir),
	}
}

func writeJSON(w http.ResponseWriter, status int, v interface{}) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	json.NewEncoder(w).Encode(v)
}

func writeErr(w http.ResponseWriter, status int, msg string) {
	writeJSON(w, status, map[string]string{"error": msg})
}

// --- Deals ---

// HandleDealsRoot handles GET /api/venture/deals (list) and POST (create).
func (h *Handlers) HandleDealsRoot(w http.ResponseWriter, r *http.Request) {
	switch r.Method {
	case http.MethodGet:
		writeJSON(w, http.StatusOK, map[string]interface{}{
			"deals": h.Deals.SnapshotAll(),
		})
	case http.MethodPost:
		var req struct {
			Name       string `json:"name"`
			Problem    string `json:"problem"`
			TargetUser string `json:"target_user"`
		}
		if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
			writeErr(w, http.StatusBadRequest, err.Error())
			return
		}
		if strings.TrimSpace(req.Name) == "" {
			writeErr(w, http.StatusBadRequest, "name required")
			return
		}
		d := h.Deals.CreateDeal(req.Name, req.Problem, req.TargetUser)
		snap, _ := h.Deals.Snapshot(d.ID)
		writeJSON(w, http.StatusCreated, snap)
	default:
		writeErr(w, http.StatusMethodNotAllowed, "GET or POST")
	}
}

// HandleDealsSubtree dispatches everything under /api/venture/deals/:
//
//	GET  /api/venture/deals/{id}
//	POST /api/venture/deals/{id}/artifacts
//	POST /api/venture/deals/{id}/risk
//	POST /api/venture/deals/{id}/approvals/{pendingId}
func (h *Handlers) HandleDealsSubtree(w http.ResponseWriter, r *http.Request) {
	path := strings.Trim(strings.TrimPrefix(r.URL.Path, "/api/venture/deals/"), "/")
	parts := strings.Split(path, "/")
	if parts[0] == "" {
		writeErr(w, http.StatusBadRequest, "deal id required")
		return
	}

	switch len(parts) {
	case 1:
		h.handleDealByID(w, r, parts[0])
	case 2:
		switch parts[1] {
		case "artifacts":
			h.handleDealArtifacts(w, r, parts[0])
		case "risk":
			h.handleDealRisk(w, r, parts[0])
		default:
			writeErr(w, http.StatusNotFound, "unknown deal sub-resource")
		}
	case 3:
		if parts[1] == "approvals" {
			h.handleDealApproval(w, r, parts[0], parts[2])
			return
		}
		writeErr(w, http.StatusNotFound, "unknown deal sub-resource")
	default:
		writeErr(w, http.StatusNotFound, "unknown deal sub-resource")
	}
}

func (h *Handlers) handleDealByID(w http.ResponseWriter, r *http.Request, id string) {
	if r.Method != http.MethodGet {
		writeErr(w, http.StatusMethodNotAllowed, "GET only")
		return
	}
	snap, ok := h.Deals.Snapshot(id)
	if !ok {
		writeErr(w, http.StatusNotFound, "deal not found")
		return
	}
	writeJSON(w, http.StatusOK, snap)
}

// handleDealArtifacts records deal progress. Local, reversible progress
// (research, repo skeletons, prototypes, drafts) is recorded immediately.
// Public or relational actions (outreach, posts, App Store submission,
// payments) are queued as a pending approval instead, per the
// autonomous-preparation / human-approved-publication rule.
func (h *Handlers) handleDealArtifacts(w http.ResponseWriter, r *http.Request, id string) {
	if r.Method != http.MethodPost {
		writeErr(w, http.StatusMethodNotAllowed, "POST only")
		return
	}
	var req struct {
		Stage    int      `json:"stage"`
		Kind     string   `json:"kind"`
		Title    string   `json:"title"`
		Content  string   `json:"content"`
		Sources  []string `json:"sources"`
		Verified bool     `json:"verified"`
	}
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeErr(w, http.StatusBadRequest, err.Error())
		return
	}
	if req.Kind == "" || req.Title == "" {
		writeErr(w, http.StatusBadRequest, "kind and title required")
		return
	}
	stage := Stage(req.Stage)
	if stage < StageIdeaCapture || stage > StageLaunchFeedback {
		writeErr(w, http.StatusBadRequest, "stage must be 1-12")
		return
	}

	artifact, pendingID, err := h.Deals.AddArtifact(id, stage, req.Kind, req.Title, req.Content, req.Sources, req.Verified)
	if err != nil {
		writeErr(w, http.StatusNotFound, err.Error())
		return
	}
	if pendingID != "" {
		writeJSON(w, http.StatusAccepted, map[string]interface{}{
			"status":     "pending_approval",
			"pending_id": pendingID,
			"reason":     "artifact kind \"" + req.Kind + "\" is gated and requires human approval before publication",
		})
		return
	}
	writeJSON(w, http.StatusCreated, artifact)
}

// handleDealApproval handles the approve/deny decision on a gated action.
func (h *Handlers) handleDealApproval(w http.ResponseWriter, r *http.Request, dealID, pendingID string) {
	if r.Method != http.MethodPost {
		writeErr(w, http.StatusMethodNotAllowed, "POST only")
		return
	}
	var req struct {
		Action string `json:"action"`
	}
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeErr(w, http.StatusBadRequest, err.Error())
		return
	}

	switch req.Action {
	case "approve":
		artifact, err := h.Deals.Approve(dealID, pendingID)
		if err != nil {
			writeErr(w, http.StatusNotFound, err.Error())
			return
		}
		writeJSON(w, http.StatusOK, artifact)
	case "deny":
		if err := h.Deals.Deny(dealID, pendingID); err != nil {
			writeErr(w, http.StatusNotFound, err.Error())
			return
		}
		writeJSON(w, http.StatusOK, map[string]string{"status": "denied"})
	default:
		writeErr(w, http.StatusBadRequest, "action must be \"approve\" or \"deny\"")
	}
}

// handleDealRisk records the novelty/competition/risk signals produced by
// prior-art and competitor research.
func (h *Handlers) handleDealRisk(w http.ResponseWriter, r *http.Request, id string) {
	if r.Method != http.MethodPost {
		writeErr(w, http.StatusMethodNotAllowed, "POST only")
		return
	}
	var req struct {
		NoveltyScore    float64 `json:"novelty_score"`
		RiskScore       float64 `json:"risk_score"`
		CompetitorCount int     `json:"competitor_count"`
	}
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeErr(w, http.StatusBadRequest, err.Error())
		return
	}
	if err := h.Deals.SetRisk(id, req.NoveltyScore, req.RiskScore, req.CompetitorCount); err != nil {
		writeErr(w, http.StatusNotFound, err.Error())
		return
	}
	snap, _ := h.Deals.Snapshot(id)
	writeJSON(w, http.StatusOK, snap)
}

// --- Breakthrough claims ---

// HandleClaimsRoot handles GET /api/venture/claims (list) and POST (create).
func (h *Handlers) HandleClaimsRoot(w http.ResponseWriter, r *http.Request) {
	switch r.Method {
	case http.MethodGet:
		writeJSON(w, http.StatusOK, map[string]interface{}{
			"claims":         h.Claims.SnapshotAll(),
			"evidence_kinds": EvidenceKinds(),
		})
	case http.MethodPost:
		var req struct {
			DealID         string `json:"deal_id"`
			Name           string `json:"name"`
			PlainClaim     string `json:"plain_claim"`
			TechnicalClaim string `json:"technical_claim"`
			NoveltyClass   string `json:"novelty_class"`
			Baseline       string `json:"baseline"`
			Experiment     string `json:"experiment"`
			PassThreshold  string `json:"pass_threshold"`
		}
		if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
			writeErr(w, http.StatusBadRequest, err.Error())
			return
		}
		if strings.TrimSpace(req.Name) == "" || strings.TrimSpace(req.TechnicalClaim) == "" {
			writeErr(w, http.StatusBadRequest, "name and technical_claim required")
			return
		}
		c := h.Claims.CreateClaim(req.DealID, req.Name, req.PlainClaim, req.TechnicalClaim, req.NoveltyClass, req.Baseline, req.Experiment, req.PassThreshold)
		snap, _ := h.Claims.Snapshot(c.ID)
		writeJSON(w, http.StatusCreated, snap)
	default:
		writeErr(w, http.StatusMethodNotAllowed, "GET or POST")
	}
}

// HandleClaimsSubtree dispatches everything under /api/venture/claims/:
//
//	GET  /api/venture/claims/{id}
//	POST /api/venture/claims/{id}/evidence
//	POST /api/venture/claims/{id}/firewall
//	POST /api/venture/claims/{id}/prior-art
//	POST /api/venture/claims/{id}/result
func (h *Handlers) HandleClaimsSubtree(w http.ResponseWriter, r *http.Request) {
	path := strings.Trim(strings.TrimPrefix(r.URL.Path, "/api/venture/claims/"), "/")
	parts := strings.Split(path, "/")
	if parts[0] == "" {
		writeErr(w, http.StatusBadRequest, "claim id required")
		return
	}

	if len(parts) == 1 {
		h.handleClaimByID(w, r, parts[0])
		return
	}
	if len(parts) == 2 {
		switch parts[1] {
		case "evidence":
			h.handleClaimEvidence(w, r, parts[0])
		case "firewall":
			h.handleClaimFirewall(w, r, parts[0])
		case "prior-art":
			h.handleClaimPriorArt(w, r, parts[0])
		case "result":
			h.handleClaimResult(w, r, parts[0])
		default:
			writeErr(w, http.StatusNotFound, "unknown claim sub-resource")
		}
		return
	}
	writeErr(w, http.StatusNotFound, "unknown claim sub-resource")
}

func (h *Handlers) handleClaimByID(w http.ResponseWriter, r *http.Request, id string) {
	if r.Method != http.MethodGet {
		writeErr(w, http.StatusMethodNotAllowed, "GET only")
		return
	}
	snap, ok := h.Claims.Snapshot(id)
	if !ok {
		writeErr(w, http.StatusNotFound, "claim not found")
		return
	}
	writeJSON(w, http.StatusOK, snap)
}

func (h *Handlers) handleClaimEvidence(w http.ResponseWriter, r *http.Request, id string) {
	if r.Method != http.MethodPost {
		writeErr(w, http.StatusMethodNotAllowed, "POST only")
		return
	}
	var req struct {
		Kind        string `json:"kind"`
		Description string `json:"description"`
		Receipt     string `json:"receipt"`
	}
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeErr(w, http.StatusBadRequest, err.Error())
		return
	}
	c, err := h.Claims.AddEvidence(id, req.Kind, req.Description, req.Receipt)
	if err != nil {
		if err == errUnknownEvidenceKind {
			writeErr(w, http.StatusBadRequest, "unknown evidence kind, must be one of: "+strings.Join(EvidenceKinds(), ", "))
			return
		}
		writeErr(w, http.StatusNotFound, err.Error())
		return
	}
	snap, _ := h.Claims.Snapshot(c.ID)
	writeJSON(w, http.StatusOK, snap)
}

// handleClaimFirewall checks whether a piece of public wording is allowed
// at the claim's current evidence tier.
func (h *Handlers) handleClaimFirewall(w http.ResponseWriter, r *http.Request, id string) {
	if r.Method != http.MethodPost {
		writeErr(w, http.StatusMethodNotAllowed, "POST only")
		return
	}
	var req struct {
		Wording string `json:"wording"`
	}
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeErr(w, http.StatusBadRequest, err.Error())
		return
	}
	c, ok := h.Claims.Get(id)
	if !ok {
		writeErr(w, http.StatusNotFound, "claim not found")
		return
	}
	violations := FirewallCheck(&c, req.Wording)
	writeJSON(w, http.StatusOK, map[string]interface{}{
		"wording":    req.Wording,
		"allowed":    len(violations) == 0,
		"tier":       int(Tier(&c)),
		"tier_name":  Tier(&c).String(),
		"violations": violations,
	})
}

// handleClaimPriorArt records a prior-art risk level. It deliberately never
// allows a stored value implying absolute clearance — callers pass a risk
// level (low/medium/high/unknown) and formal legal review remains a human
// step.
func (h *Handlers) handleClaimPriorArt(w http.ResponseWriter, r *http.Request, id string) {
	if r.Method != http.MethodPost {
		writeErr(w, http.StatusMethodNotAllowed, "POST only")
		return
	}
	var req struct {
		Risk string `json:"risk"`
	}
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeErr(w, http.StatusBadRequest, err.Error())
		return
	}
	switch req.Risk {
	case "low", "medium", "high", "unknown":
	default:
		writeErr(w, http.StatusBadRequest, "risk must be one of: low, medium, high, unknown")
		return
	}
	if err := h.Claims.SetPriorArtRisk(id, req.Risk); err != nil {
		writeErr(w, http.StatusNotFound, err.Error())
		return
	}
	snap, _ := h.Claims.Snapshot(id)
	writeJSON(w, http.StatusOK, snap)
}

// handleClaimResult records a measured result summary for the claim's
// experiment.
func (h *Handlers) handleClaimResult(w http.ResponseWriter, r *http.Request, id string) {
	if r.Method != http.MethodPost {
		writeErr(w, http.StatusMethodNotAllowed, "POST only")
		return
	}
	var req struct {
		Summary string `json:"summary"`
	}
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeErr(w, http.StatusBadRequest, err.Error())
		return
	}
	if err := h.Claims.SetResultSummary(id, req.Summary); err != nil {
		writeErr(w, http.StatusNotFound, err.Error())
		return
	}
	snap, _ := h.Claims.Snapshot(id)
	writeJSON(w, http.StatusOK, snap)
}
