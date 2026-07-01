// Breakthrough Verification Engine: decides whether an idea or result
// deserves to be treated as a breakthrough candidate. It does not grant
// "breakthrough" status by fiat — it tracks the evidence a claim has
// actually accumulated (implementation, tests, baselines, ablations,
// repetition, external reproduction) and blocks public wording that
// outruns that evidence.
//
// Doctrine: no breakthrough claim without falsification, no novelty claim
// without prior-art search, no performance claim without baseline, no
// research claim without reproducibility.
package venture

import (
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"time"
)

// EvidenceTier is the ladder from bare concept to commercializable
// breakthrough. A claim's tier is derived from its EvidenceScore, never
// set directly.
type EvidenceTier int

const (
	TierConcept EvidenceTier = iota
	TierImplemented
	TierRuns
	TierStable
	TierBaselineBeating
	TierAblationProven
	TierReproducible
	TierGeneralized
	TierExternallyVerified
	TierScientificContribution
	TierCommercializableBreakthrough
)

var tierNames = map[EvidenceTier]string{
	TierConcept:                      "concept",
	TierImplemented:                  "implemented",
	TierRuns:                         "runs",
	TierStable:                       "stable",
	TierBaselineBeating:              "baseline_beating",
	TierAblationProven:               "ablation_proven",
	TierReproducible:                 "reproducible",
	TierGeneralized:                  "generalized",
	TierExternallyVerified:           "externally_verified",
	TierScientificContribution:       "scientific_contribution",
	TierCommercializableBreakthrough: "commercializable_breakthrough",
}

func (t EvidenceTier) String() string {
	if n, ok := tierNames[t]; ok {
		return n
	}
	return "unknown"
}

// Evidence is one piece of proof attached to a claim. Kind must be one of
// the keys in evidenceWeight.
type Evidence struct {
	ID          string    `json:"id"`
	Kind        string    `json:"kind"`
	Description string    `json:"description"`
	Receipt     string    `json:"receipt,omitempty"` // hash, log path, or run ID
	AddedAt     time.Time `json:"added_at"`
}

// evidenceWeight mirrors the doc's evidence-weight table; the weights sum
// to 100 so EvidenceScore is a 0-100 confidence number.
var evidenceWeight = map[string]float64{
	"implementation":        10,
	"clean_build":           10,
	"unit_tests":            10,
	"smoke_test":            15,
	"baseline_comparison":   15,
	"ablation":              15,
	"repeated_seeds":        10,
	"real_world_task":       10,
	"external_reproduction": 5,
}

// EvidenceKinds lists the recognized evidence kinds, for validation by callers.
func EvidenceKinds() []string {
	out := make([]string, 0, len(evidenceWeight))
	for k := range evidenceWeight {
		out = append(out, k)
	}
	return out
}

// tierThresholds maps the minimum EvidenceScore required to reach a tier.
// A tier also requires the specific evidence kind associated with it, not
// just accumulated score, so a claim can't reach ablation-proven purely by
// stacking unit tests.
var tierRequiredKind = map[EvidenceTier]string{
	TierImplemented:        "implementation",
	TierRuns:               "clean_build",
	TierStable:             "smoke_test",
	TierBaselineBeating:    "baseline_comparison",
	TierAblationProven:     "ablation",
	TierReproducible:       "repeated_seeds",
	TierGeneralized:        "real_world_task",
	TierExternallyVerified: "external_reproduction",
}

// wordingRules gates strong public claims behind a minimum evidence tier.
// Wording not matched by any rule is always allowed (it is treated as
// evidence-neutral phrasing).
var wordingRules = []struct {
	phrase  string
	minTier EvidenceTier
}{
	{"breakthrough", TierScientificContribution},
	{"revolutionary", TierScientificContribution},
	{"world-first", TierExternallyVerified},
	{"world first", TierExternallyVerified},
	{"frontier", TierExternallyVerified},
	{"proven", TierAblationProven},
	{"state of the art", TierBaselineBeating},
	{"state-of-the-art", TierBaselineBeating},
	{"beats", TierBaselineBeating},
	{"outperforms", TierBaselineBeating},
	{"validated", TierReproducible},
}

// ClaimCard is a single testable claim extracted from an idea or result,
// tracked from unverified hypothesis to (at most) validated contribution.
type ClaimCard struct {
	ID             string     `json:"id"`
	DealID         string     `json:"deal_id,omitempty"`
	Name           string     `json:"name"`
	PlainClaim     string     `json:"plain_claim"`
	TechnicalClaim string     `json:"technical_claim"`
	NoveltyClass   string     `json:"novelty_class"`
	PriorArtRisk   string     `json:"prior_art_risk"` // low, medium, high, unknown
	Baseline       string     `json:"baseline"`
	Experiment     string     `json:"experiment"`
	PassThreshold  string     `json:"pass_threshold"`
	ResultSummary  string     `json:"result_summary"`
	Evidence       []Evidence `json:"evidence"`
	CreatedAt      time.Time  `json:"created_at"`
	UpdatedAt      time.Time  `json:"updated_at"`
}

// ClaimSnapshot is the derived, API-facing view of a ClaimCard.
type ClaimSnapshot struct {
	ClaimCard
	EvidenceScore    float64  `json:"evidence_score"`
	EvidenceTier     int      `json:"evidence_tier"`
	EvidenceTierName string   `json:"evidence_tier_name"`
	AllowedWording   []string `json:"allowed_wording_examples"`
	BlockedWording   []string `json:"blocked_wording_examples"`
}

// ClaimStore holds claim cards in memory and persists them to disk,
// mirroring venture.Store.
type ClaimStore struct {
	mu     sync.RWMutex
	claims map[string]*ClaimCard
	path   string
}

// NewClaimStore creates a ClaimStore persisting to
// <dataDir>/breakthrough_claims.json.
func NewClaimStore(dataDir string) *ClaimStore {
	cs := &ClaimStore{
		claims: make(map[string]*ClaimCard),
		path:   filepath.Join(dataDir, "breakthrough_claims.json"),
	}
	cs.load()
	return cs
}

// CreateClaim registers a new, unverified claim. It starts with zero
// evidence at TierConcept.
func (cs *ClaimStore) CreateClaim(dealID, name, plainClaim, technicalClaim, noveltyClass, baseline, experiment, passThreshold string) ClaimCard {
	cs.mu.Lock()
	defer cs.mu.Unlock()

	now := time.Now()
	c := &ClaimCard{
		ID:             "claim_" + randomHex(8),
		DealID:         dealID,
		Name:           name,
		PlainClaim:     plainClaim,
		TechnicalClaim: technicalClaim,
		NoveltyClass:   noveltyClass,
		PriorArtRisk:   "unknown",
		Baseline:       baseline,
		Experiment:     experiment,
		PassThreshold:  passThreshold,
		CreatedAt:      now,
		UpdatedAt:      now,
	}
	cs.claims[c.ID] = c
	cs.persistLocked()
	return *c
}

// Get returns a copy of the claim, and whether it exists.
func (cs *ClaimStore) Get(id string) (ClaimCard, bool) {
	cs.mu.RLock()
	defer cs.mu.RUnlock()
	c, ok := cs.claims[id]
	if !ok {
		return ClaimCard{}, false
	}
	return *c, true
}

// List returns all claims, most recently updated first.
func (cs *ClaimStore) List() []ClaimCard {
	cs.mu.RLock()
	defer cs.mu.RUnlock()
	out := make([]ClaimCard, 0, len(cs.claims))
	for _, c := range cs.claims {
		out = append(out, *c)
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

// SetPriorArtRisk records the outcome of a prior-art search. It never
// claims "no prior art" — only a risk level and, implicitly, that a
// formal legal review is still required to rely on it.
func (cs *ClaimStore) SetPriorArtRisk(claimID, risk string) error {
	cs.mu.Lock()
	defer cs.mu.Unlock()
	c, ok := cs.claims[claimID]
	if !ok {
		return errClaimNotFound
	}
	c.PriorArtRisk = risk
	c.UpdatedAt = time.Now()
	cs.persistLocked()
	return nil
}

// SetResultSummary records the measured outcome of the claim's experiment.
func (cs *ClaimStore) SetResultSummary(claimID, summary string) error {
	cs.mu.Lock()
	defer cs.mu.Unlock()
	c, ok := cs.claims[claimID]
	if !ok {
		return errClaimNotFound
	}
	c.ResultSummary = summary
	c.UpdatedAt = time.Now()
	cs.persistLocked()
	return nil
}

// AddEvidence attaches one piece of evidence (unrecognized kinds are
// rejected so the evidence score stays well-defined).
func (cs *ClaimStore) AddEvidence(claimID, kind, description, receipt string) (ClaimCard, error) {
	cs.mu.Lock()
	defer cs.mu.Unlock()

	c, ok := cs.claims[claimID]
	if !ok {
		return ClaimCard{}, errClaimNotFound
	}
	if _, known := evidenceWeight[kind]; !known {
		return ClaimCard{}, errUnknownEvidenceKind
	}

	c.Evidence = append(c.Evidence, Evidence{
		ID:          "evidence_" + randomHex(8),
		Kind:        kind,
		Description: description,
		Receipt:     receipt,
		AddedAt:     time.Now(),
	})
	c.UpdatedAt = time.Now()
	cs.persistLocked()
	return *c, nil
}

// EvidenceScore sums the weights of every distinct evidence kind attached
// to the claim (0-100). Repeating the same kind does not inflate the
// score — only the presence of each kind counts.
func EvidenceScore(c *ClaimCard) float64 {
	present := map[string]bool{}
	for _, e := range c.Evidence {
		present[e.Kind] = true
	}
	score := 0.0
	for kind := range present {
		score += evidenceWeight[kind]
	}
	return score
}

// Tier walks the evidence-tier ladder and returns the highest tier whose
// required evidence kind is present. Tiers are gated on specific evidence,
// not on cumulative score, matching the doctrine that a claim shouldn't
// leapfrog to "ablation-proven" merely by piling up unit tests.
func Tier(c *ClaimCard) EvidenceTier {
	present := map[string]bool{}
	for _, e := range c.Evidence {
		present[e.Kind] = true
	}
	tier := TierConcept
	ladder := []EvidenceTier{
		TierImplemented, TierRuns, TierStable, TierBaselineBeating,
		TierAblationProven, TierReproducible, TierGeneralized, TierExternallyVerified,
	}
	for _, t := range ladder {
		kind := tierRequiredKind[t]
		if present[kind] {
			tier = t
		} else {
			break
		}
	}
	// Tiers 9 and 10 (scientific contribution / commercializable
	// breakthrough) are never awarded automatically — they require
	// explicit human sign-off via PromoteToContribution, on top of
	// reaching TierExternallyVerified.
	return tier
}

// FirewallCheck decides whether a piece of public wording is allowed for a
// claim at its current evidence tier. It returns the rules the wording
// tripped, if any; an empty slice means the wording is allowed.
func FirewallCheck(c *ClaimCard, wording string) []string {
	lower := strings.ToLower(wording)
	tier := Tier(c)
	var violations []string
	for _, rule := range wordingRules {
		if strings.Contains(lower, rule.phrase) && tier < rule.minTier {
			violations = append(violations, "phrase \""+rule.phrase+"\" requires tier >= "+rule.minTier.String()+" but claim is at "+tier.String())
		}
	}
	return violations
}

// Snapshot computes the derived view of a claim: evidence score, tier, and
// illustrative allowed/blocked wording at the current tier.
func (cs *ClaimStore) Snapshot(claimID string) (ClaimSnapshot, bool) {
	cs.mu.RLock()
	defer cs.mu.RUnlock()
	c, ok := cs.claims[claimID]
	if !ok {
		return ClaimSnapshot{}, false
	}
	return snapshotClaimLocked(c), true
}

// SnapshotAll returns snapshots for every claim, most recently updated first.
func (cs *ClaimStore) SnapshotAll() []ClaimSnapshot {
	cs.mu.RLock()
	defer cs.mu.RUnlock()
	out := make([]ClaimSnapshot, 0, len(cs.claims))
	for _, c := range cs.claims {
		out = append(out, snapshotClaimLocked(c))
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

func snapshotClaimLocked(c *ClaimCard) ClaimSnapshot {
	tier := Tier(c)
	var allowed, blocked []string
	for _, rule := range wordingRules {
		if tier >= rule.minTier {
			allowed = append(allowed, rule.phrase)
		} else {
			blocked = append(blocked, rule.phrase)
		}
	}

	cp := *c
	cp.Evidence = append([]Evidence{}, c.Evidence...)

	return ClaimSnapshot{
		ClaimCard:        cp,
		EvidenceScore:    EvidenceScore(c),
		EvidenceTier:     int(tier),
		EvidenceTierName: tier.String(),
		AllowedWording:   allowed,
		BlockedWording:   blocked,
	}
}

func (cs *ClaimStore) persistLocked() {
	data, err := json.MarshalIndent(cs.claims, "", "  ")
	if err != nil {
		return
	}
	os.WriteFile(cs.path, data, 0644)
}

func (cs *ClaimStore) load() {
	data, err := os.ReadFile(cs.path)
	if err != nil {
		return
	}
	var loaded map[string]*ClaimCard
	if err := json.Unmarshal(data, &loaded); err != nil {
		return
	}
	cs.mu.Lock()
	defer cs.mu.Unlock()
	cs.claims = loaded
}
