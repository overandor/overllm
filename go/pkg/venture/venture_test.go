package venture

import (
	"testing"
)

func TestMaturityScoreAdvancesWithStages(t *testing.T) {
	dir := t.TempDir()
	st := NewStore(dir)

	d := st.CreateDeal("Test Deal", "problem", "user")
	snap, ok := st.Snapshot(d.ID)
	if !ok {
		t.Fatal("expected deal to exist")
	}
	if snap.MaturityScore != 0 {
		t.Fatalf("expected 0 maturity score for a bare deal, got %v", snap.MaturityScore)
	}

	if _, _, err := st.AddArtifact(d.ID, StageIdeaCapture, "idea_brief", "Idea Brief", "content", nil, true); err != nil {
		t.Fatalf("AddArtifact: %v", err)
	}

	snap, _ = st.Snapshot(d.ID)
	if snap.StagesComplete != 1 {
		t.Fatalf("expected 1 completed stage, got %d", snap.StagesComplete)
	}
	if snap.MaturityScore <= 0 {
		t.Fatalf("expected maturity score to increase after an artifact, got %v", snap.MaturityScore)
	}
	if snap.CurrentStage != StageIdeaCapture {
		t.Fatalf("expected current stage to be idea capture, got %v", snap.CurrentStage)
	}
}

func TestGatedArtifactRequiresApproval(t *testing.T) {
	dir := t.TempDir()
	st := NewStore(dir)
	d := st.CreateDeal("Test Deal", "problem", "user")

	artifact, pendingID, err := st.AddArtifact(d.ID, StageTeamFormation, "outreach_sent", "Ask a friend for design help", "draft message", nil, false)
	if err != nil {
		t.Fatalf("AddArtifact: %v", err)
	}
	if pendingID == "" {
		t.Fatal("expected gated artifact kind to produce a pending approval id")
	}
	if artifact.ID != "" {
		t.Fatal("expected no artifact to be recorded before approval")
	}

	snap, _ := st.Snapshot(d.ID)
	if len(snap.Pending) != 1 {
		t.Fatalf("expected 1 pending approval, got %d", len(snap.Pending))
	}
	if snap.StagesComplete != 0 {
		t.Fatal("a pending gated action must not count as stage progress")
	}

	approved, err := st.Approve(d.ID, pendingID)
	if err != nil {
		t.Fatalf("Approve: %v", err)
	}
	if !approved.Verified {
		t.Fatal("approved artifact should be marked verified")
	}

	snap, _ = st.Snapshot(d.ID)
	if len(snap.Pending) != 0 {
		t.Fatal("expected pending approval to be cleared after approval")
	}
	if snap.StagesComplete != 1 {
		t.Fatalf("expected approved artifact to count toward stage progress, got %d", snap.StagesComplete)
	}
}

func TestEvidenceTierRequiresSpecificEvidence(t *testing.T) {
	dir := t.TempDir()
	cs := NewClaimStore(dir)
	c := cs.CreateClaim("", "Bounded Q", "plain", "HotTensorC bounds Q-values", "efficiency", "old baseline", "smoke test", "no NaN/crash")

	if tier := Tier(&c); tier != TierConcept {
		t.Fatalf("expected fresh claim at TierConcept, got %v", tier)
	}

	// Piling up unit tests should not skip ahead to baseline-beating.
	if _, err := cs.AddEvidence(c.ID, "unit_tests", "unit tests pass", ""); err != nil {
		t.Fatalf("AddEvidence: %v", err)
	}
	c, _ = cs.Get(c.ID)
	if tier := Tier(&c); tier != TierConcept {
		t.Fatalf("unit tests alone should not advance the tier ladder, got %v", tier)
	}

	if _, err := cs.AddEvidence(c.ID, "implementation", "code exists", ""); err != nil {
		t.Fatalf("AddEvidence: %v", err)
	}
	if _, err := cs.AddEvidence(c.ID, "clean_build", "builds", ""); err != nil {
		t.Fatalf("AddEvidence: %v", err)
	}
	if _, err := cs.AddEvidence(c.ID, "smoke_test", "1000/1000 steps, no NaN/crash", "hash:abc123"); err != nil {
		t.Fatalf("AddEvidence: %v", err)
	}
	c, _ = cs.Get(c.ID)
	if tier := Tier(&c); tier != TierStable {
		t.Fatalf("expected TierStable after implementation+build+smoke test, got %v", tier)
	}

	if _, err := cs.AddEvidence(c.ID, "not_a_real_kind", "x", ""); err == nil {
		t.Fatal("expected unknown evidence kind to be rejected")
	}
}

func TestFirewallBlocksOverclaiming(t *testing.T) {
	dir := t.TempDir()
	cs := NewClaimStore(dir)
	c := cs.CreateClaim("", "Bounded Q", "plain", "technical", "efficiency", "baseline", "experiment", "threshold")

	violations := FirewallCheck(&c, "This is a breakthrough result.")
	if len(violations) == 0 {
		t.Fatal("expected an unverified claim to be blocked from using the word breakthrough")
	}

	allowed := FirewallCheck(&c, "Internally stable in a 1000-action smoke test.")
	if len(allowed) != 0 {
		t.Fatalf("expected evidence-neutral wording to be allowed, got violations: %v", allowed)
	}

	// Reach TierStable and confirm "state of the art" (baseline-beating)
	// is still blocked, but a stable-tier-appropriate claim would need
	// baseline_comparison evidence specifically.
	cs.AddEvidence(c.ID, "implementation", "code exists", "")
	cs.AddEvidence(c.ID, "clean_build", "builds", "")
	cs.AddEvidence(c.ID, "smoke_test", "smoke test passes", "")
	c, _ = cs.Get(c.ID)
	if v := FirewallCheck(&c, "beats the old baseline"); len(v) == 0 {
		t.Fatal("expected baseline-beating wording to still require baseline_comparison evidence")
	}

	cs.AddEvidence(c.ID, "baseline_comparison", "beats old GodLearner on fake-success rate", "")
	c, _ = cs.Get(c.ID)
	if v := FirewallCheck(&c, "beats the old baseline"); len(v) != 0 {
		t.Fatalf("expected baseline-beating wording to be allowed once baseline_comparison evidence exists, got %v", v)
	}
}
