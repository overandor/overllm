// Package venture implements VentureChain: the artifact pipeline that turns
// a raw idea into a receipt-backed venture packet by walking it through the
// twelve stages of deal formation (idea capture through launch/feedback).
//
// Every action against a Deal is scored against one question: did it move
// the deal state forward? Progress is measured by artifacts attached to
// stages, not by the number of actions taken.
package venture

import (
	"crypto/rand"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"os"
	"path/filepath"
	"sync"
	"time"
)

var (
	errDealNotFound        = errors.New("deal not found")
	errPendingNotFound     = errors.New("pending approval not found")
	errClaimNotFound       = errors.New("claim not found")
	errUnknownEvidenceKind = errors.New("unknown evidence kind")
)

// Stage is a step in the deal-formation chain: idea -> ... -> launch.
type Stage int

const (
	StageIdeaCapture Stage = iota + 1
	StagePriorArtScan
	StageCompetitionMap
	StageEconomicThesis
	StageFeasibilityPlan
	StageTeamFormation
	StageRepoFormation
	StagePrototype
	StageLandingPage
	StageWebFunctionality
	StageDistributionPack
	StageLaunchFeedback
)

var stageNames = map[Stage]string{
	StageIdeaCapture:      "idea_capture",
	StagePriorArtScan:     "prior_art_scan",
	StageCompetitionMap:   "competition_map",
	StageEconomicThesis:   "economic_thesis",
	StageFeasibilityPlan:  "feasibility_plan",
	StageTeamFormation:    "team_formation",
	StageRepoFormation:    "repo_formation",
	StagePrototype:        "prototype",
	StageLandingPage:      "landing_page",
	StageWebFunctionality: "web_functionality",
	StageDistributionPack: "distribution_pack",
	StageLaunchFeedback:   "launch_feedback",
}

// expectedArtifactKind is the artifact kind that satisfies each stage, per
// the deal-closing chain: idea brief, novelty report, competition matrix,
// monetization thesis, technical blueprint, team-request brief, repo
// skeleton, prototype, landing page, web surface, distribution packet,
// launch report.
var expectedArtifactKind = map[Stage]string{
	StageIdeaCapture:      "idea_brief",
	StagePriorArtScan:     "novelty_report",
	StageCompetitionMap:   "competition_matrix",
	StageEconomicThesis:   "monetization_thesis",
	StageFeasibilityPlan:  "technical_blueprint",
	StageTeamFormation:    "team_request_brief",
	StageRepoFormation:    "repo_skeleton",
	StagePrototype:        "prototype",
	StageLandingPage:      "landing_page",
	StageWebFunctionality: "web_surface",
	StageDistributionPack: "distribution_packet",
	StageLaunchFeedback:   "launch_report",
}

func allStages() []Stage {
	return []Stage{
		StageIdeaCapture, StagePriorArtScan, StageCompetitionMap, StageEconomicThesis,
		StageFeasibilityPlan, StageTeamFormation, StageRepoFormation, StagePrototype,
		StageLandingPage, StageWebFunctionality, StageDistributionPack, StageLaunchFeedback,
	}
}

func (s Stage) String() string {
	if n, ok := stageNames[s]; ok {
		return n
	}
	return "unknown"
}

// gatedArtifactKinds are public or relational actions that must never be
// attached autonomously. They require an explicit approval before the
// artifact is recorded as complete. Local, reversible artifacts (research
// notes, repo skeletons, prototypes, drafts) are not in this set.
var gatedArtifactKinds = map[string]bool{
	"outreach_sent":       true,
	"public_post":         true,
	"appstore_submission": true,
	"domain_purchase":     true,
	"payment_charge":      true,
	"investor_outreach":   true,
	"email_sent":          true,
}

// IsGated reports whether attaching an artifact of this kind requires human
// approval before it can be recorded as done, per the rule: autonomous
// preparation, human-approved publication.
func IsGated(kind string) bool {
	return gatedArtifactKinds[kind]
}

// Artifact is a produced unit of deal progress: an idea brief, a novelty
// report, a repo skeleton, a landing page draft, and so on.
type Artifact struct {
	ID        string    `json:"id"`
	Stage     Stage     `json:"stage"`
	StageName string    `json:"stage_name"`
	Kind      string    `json:"kind"`
	Title     string    `json:"title"`
	Content   string    `json:"content"`
	Sources   []string  `json:"sources,omitempty"`
	Verified  bool      `json:"verified"`
	Hash      string    `json:"hash"`
	CreatedAt time.Time `json:"created_at"`
}

// PendingApproval is a gated action awaiting explicit human sign-off before
// it can be recorded as an artifact.
type PendingApproval struct {
	ID          string    `json:"id"`
	DealID      string    `json:"deal_id"`
	Stage       Stage     `json:"stage"`
	StageName   string    `json:"stage_name"`
	Kind        string    `json:"kind"`
	Title       string    `json:"title"`
	Content     string    `json:"content"`
	Sources     []string  `json:"sources,omitempty"`
	RequestedAt time.Time `json:"requested_at"`
}

// Deal is the central object tracked by VentureChain: where one idea
// currently sits in the money chain. Deal values are only ever mutated
// while the owning Store's lock is held; callers must go through Store
// methods rather than mutating a Deal directly.
type Deal struct {
	ID         string `json:"id"`
	Name       string `json:"name"`
	Problem    string `json:"problem"`
	TargetUser string `json:"target_user"`

	CurrentStage Stage             `json:"current_stage"`
	Artifacts    []Artifact        `json:"artifacts"`
	Pending      []PendingApproval `json:"pending_approvals"`

	NoveltyScore    float64 `json:"novelty_score"` // 0-1, higher = more novel
	RiskScore       float64 `json:"risk_score"`    // 0-1, higher = riskier
	CompetitorCount int     `json:"competitor_count"`

	CreatedAt time.Time `json:"created_at"`
	UpdatedAt time.Time `json:"updated_at"`
}

// DealSnapshot is the JSON-safe view of a Deal returned by the API,
// including derived fields that are not stored directly.
type DealSnapshot struct {
	Deal
	MaturityScore  float64 `json:"maturity_score"`
	StagesComplete int     `json:"stages_complete"`
	StagesTotal    int     `json:"stages_total"`
	NextBestAction string  `json:"next_best_action"`
	VerifiedCount  int     `json:"verified_artifact_count"`
}

// Store holds all deals in memory and persists them to disk as JSON,
// mirroring the AgentMemory persistence pattern used elsewhere in overagent.
// A single lock guards both the deals map and every Deal reachable from it.
type Store struct {
	mu    sync.RWMutex
	deals map[string]*Deal
	path  string
}

// NewStore creates a Store that persists to <dataDir>/venture_deals.json.
func NewStore(dataDir string) *Store {
	st := &Store{
		deals: make(map[string]*Deal),
		path:  filepath.Join(dataDir, "venture_deals.json"),
	}
	st.load()
	return st
}

// CreateDeal starts a new deal at Stage 1 (idea capture).
func (st *Store) CreateDeal(name, problem, targetUser string) Deal {
	st.mu.Lock()
	defer st.mu.Unlock()

	now := time.Now()
	d := &Deal{
		ID:           "deal_" + randomHex(8),
		Name:         name,
		Problem:      problem,
		TargetUser:   targetUser,
		CurrentStage: StageIdeaCapture,
		CreatedAt:    now,
		UpdatedAt:    now,
	}
	st.deals[d.ID] = d
	st.persistLocked()
	return *d
}

// Get returns a copy of the deal with the given ID, and whether it exists.
func (st *Store) Get(id string) (Deal, bool) {
	st.mu.RLock()
	defer st.mu.RUnlock()
	d, ok := st.deals[id]
	if !ok {
		return Deal{}, false
	}
	return *d, true
}

// List returns a copy of all deals sorted by most recently updated.
func (st *Store) List() []Deal {
	st.mu.RLock()
	defer st.mu.RUnlock()
	out := make([]Deal, 0, len(st.deals))
	for _, d := range st.deals {
		out = append(out, *d)
	}
	for i := 0; i < len(out); i++ {
		for j := i + 1; j < len(out); j++ {
			if out[j].UpdatedAt.After(out[i].UpdatedAt) {
				out[i], out[j] = out[j], out[i]
			}
		}
	}
	return out
}

// AddArtifact records deal progress. Gated artifact kinds are queued as a
// PendingApproval instead of being recorded immediately; call Approve to
// release them. Returns the artifact if recorded immediately, or an empty
// artifact plus the pending approval ID if it was gated.
func (st *Store) AddArtifact(dealID string, stage Stage, kind, title, content string, sources []string, verified bool) (Artifact, string, error) {
	st.mu.Lock()
	defer st.mu.Unlock()

	d, ok := st.deals[dealID]
	if !ok {
		return Artifact{}, "", errDealNotFound
	}

	if IsGated(kind) {
		pa := PendingApproval{
			ID:          "pending_" + randomHex(8),
			DealID:      dealID,
			Stage:       stage,
			StageName:   stage.String(),
			Kind:        kind,
			Title:       title,
			Content:     content,
			Sources:     sources,
			RequestedAt: time.Now(),
		}
		d.Pending = append(d.Pending, pa)
		d.UpdatedAt = time.Now()
		st.persistLocked()
		return Artifact{}, pa.ID, nil
	}

	a := Artifact{
		ID:        "artifact_" + randomHex(8),
		Stage:     stage,
		StageName: stage.String(),
		Kind:      kind,
		Title:     title,
		Content:   content,
		Sources:   sources,
		Verified:  verified,
		Hash:      hashContent(kind + "|" + title + "|" + content),
		CreatedAt: time.Now(),
	}
	d.Artifacts = append(d.Artifacts, a)
	if stage > d.CurrentStage {
		d.CurrentStage = stage
	}
	d.UpdatedAt = time.Now()
	st.persistLocked()
	return a, "", nil
}

// Approve releases a pending gated action, recording it as a real artifact.
// This is the only path by which a gated artifact kind (outreach, public
// posts, App Store submission, payments, ...) becomes part of the deal.
func (st *Store) Approve(dealID, pendingID string) (Artifact, error) {
	st.mu.Lock()
	defer st.mu.Unlock()

	d, ok := st.deals[dealID]
	if !ok {
		return Artifact{}, errDealNotFound
	}

	idx := -1
	for i, p := range d.Pending {
		if p.ID == pendingID {
			idx = i
			break
		}
	}
	if idx == -1 {
		return Artifact{}, errPendingNotFound
	}
	p := d.Pending[idx]
	d.Pending = append(d.Pending[:idx], d.Pending[idx+1:]...)

	a := Artifact{
		ID:        "artifact_" + randomHex(8),
		Stage:     p.Stage,
		StageName: p.StageName,
		Kind:      p.Kind,
		Title:     p.Title,
		Content:   p.Content,
		Sources:   p.Sources,
		Verified:  true,
		Hash:      hashContent(p.Kind + "|" + p.Title + "|" + p.Content),
		CreatedAt: time.Now(),
	}
	d.Artifacts = append(d.Artifacts, a)
	if p.Stage > d.CurrentStage {
		d.CurrentStage = p.Stage
	}
	d.UpdatedAt = time.Now()
	st.persistLocked()
	return a, nil
}

// Deny discards a pending gated action without recording an artifact.
func (st *Store) Deny(dealID, pendingID string) error {
	st.mu.Lock()
	defer st.mu.Unlock()

	d, ok := st.deals[dealID]
	if !ok {
		return errDealNotFound
	}
	for i, p := range d.Pending {
		if p.ID == pendingID {
			d.Pending = append(d.Pending[:i], d.Pending[i+1:]...)
			d.UpdatedAt = time.Now()
			st.persistLocked()
			return nil
		}
	}
	return errPendingNotFound
}

// SetRisk updates the novelty/risk/competition signals used by the
// maturity score.
func (st *Store) SetRisk(dealID string, noveltyScore, riskScore float64, competitorCount int) error {
	st.mu.Lock()
	defer st.mu.Unlock()

	d, ok := st.deals[dealID]
	if !ok {
		return errDealNotFound
	}
	d.NoveltyScore = noveltyScore
	d.RiskScore = riskScore
	d.CompetitorCount = competitorCount
	d.UpdatedAt = time.Now()
	st.persistLocked()
	return nil
}

// Snapshot computes the derived venture-maturity view of a deal: how many
// of the twelve stages have a recorded artifact, a 0-100 maturity score,
// and the next best economic action.
func (st *Store) Snapshot(dealID string) (DealSnapshot, bool) {
	st.mu.RLock()
	defer st.mu.RUnlock()

	d, ok := st.deals[dealID]
	if !ok {
		return DealSnapshot{}, false
	}
	return snapshotLocked(d), true
}

// SnapshotAll returns maturity snapshots for every deal, most recently
// updated first.
func (st *Store) SnapshotAll() []DealSnapshot {
	st.mu.RLock()
	defer st.mu.RUnlock()

	out := make([]DealSnapshot, 0, len(st.deals))
	for _, d := range st.deals {
		out = append(out, snapshotLocked(d))
	}
	for i := 0; i < len(out); i++ {
		for j := i + 1; j < len(out); j++ {
			if out[j].UpdatedAt.After(out[i].UpdatedAt) {
				out[i], out[j] = out[j], out[i]
			}
		}
	}
	return out
}

func snapshotLocked(d *Deal) DealSnapshot {
	stageHasArtifact := map[Stage]bool{}
	verifiedCount := 0
	for _, a := range d.Artifacts {
		stageHasArtifact[a.Stage] = true
		if a.Verified {
			verifiedCount++
		}
	}

	stages := allStages()
	complete := 0
	var nextStage Stage
	for _, s := range stages {
		if stageHasArtifact[s] {
			complete++
		} else if nextStage == 0 {
			nextStage = s
		}
	}

	// Each completed stage is worth an equal share of the base score.
	// A verified artifact within a stage earns a small bonus, capped so
	// the score never exceeds 100.
	base := float64(complete) / float64(len(stages)) * 90.0
	bonus := float64(verifiedCount) / float64(len(d.Artifacts)+1) * 10.0
	score := base + bonus
	if score > 100 {
		score = 100
	}

	nextAction := "Deal is fully staged; monitor launch feedback and iterate."
	if nextStage != 0 {
		nextAction = "Produce " + expectedArtifactKind[nextStage] + " to advance stage " + nextStage.String()
	}
	if len(d.Pending) > 0 {
		nextAction = "Awaiting human approval on pending gated action(s) before proceeding"
	}

	cp := *d
	cp.Artifacts = append([]Artifact{}, d.Artifacts...)
	cp.Pending = append([]PendingApproval{}, d.Pending...)

	return DealSnapshot{
		Deal:           cp,
		MaturityScore:  score,
		StagesComplete: complete,
		StagesTotal:    len(stages),
		NextBestAction: nextAction,
		VerifiedCount:  verifiedCount,
	}
}

// persistLocked writes the store to disk. Callers must hold st.mu (read or
// write lock) before calling.
func (st *Store) persistLocked() {
	data, err := json.MarshalIndent(st.deals, "", "  ")
	if err != nil {
		return
	}
	os.WriteFile(st.path, data, 0644)
}

func (st *Store) load() {
	data, err := os.ReadFile(st.path)
	if err != nil {
		return
	}
	var loaded map[string]*Deal
	if err := json.Unmarshal(data, &loaded); err != nil {
		return
	}
	st.mu.Lock()
	defer st.mu.Unlock()
	st.deals = loaded
}

func randomHex(n int) string {
	b := make([]byte, n)
	rand.Read(b)
	return hex.EncodeToString(b)
}

func hashContent(s string) string {
	h := sha256.Sum256([]byte(s))
	return hex.EncodeToString(h[:])
}
