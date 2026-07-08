package localmodel

import (
	"context"
	"errors"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"time"
)

// Result is the structured response returned by the local inference runner.
type Result struct {
	Text       string `json:"text"`
	Runtime    string `json:"runtime"`
	ModelPath  string `json:"model_path"`
	VocabPath  string `json:"vocab_path"`
	PromptHash string `json:"prompt_hash,omitempty"`
	TruthLabel string `json:"truth_label"`
}

// Runner wraps the compiled C++ inference binary. It intentionally shells out to
// the standalone executable instead of linking unsafe process-global state into
// the Go HTTP server.
type Runner struct {
	BinaryPath string
	VocabPath  string
	ModelPath  string
	Timeout    time.Duration
}

// NewFromEnv creates a runner from environment variables while preserving sane
// local defaults for the repository root.
func NewFromEnv() (*Runner, error) {
	timeout := 60 * time.Second
	if raw := os.Getenv("OVERLLM_MODEL_TIMEOUT"); raw != "" {
		parsed, err := time.ParseDuration(raw)
		if err != nil {
			return nil, fmt.Errorf("invalid OVERLLM_MODEL_TIMEOUT: %w", err)
		}
		timeout = parsed
	}

	r := &Runner{
		BinaryPath: envOrDefault("OVERLLM_INFERENCE_BINARY", "./overllm_inference"),
		VocabPath:  envOrDefault("OVERLLM_VOCAB_PATH", "./vocab.txt"),
		ModelPath:  envOrDefault("OVERLLM_MODEL_PATH", "./models/overllm.bin"),
		Timeout:    timeout,
	}
	return r, nil
}

func envOrDefault(key, fallback string) string {
	if val := os.Getenv(key); val != "" {
		return val
	}
	return fallback
}

// Validate checks that the configured runtime files exist and are usable.
func (r *Runner) Validate() error {
	if r == nil {
		return errors.New("runner is nil")
	}
	checks := map[string]string{
		"inference binary": r.BinaryPath,
		"vocabulary":       r.VocabPath,
		"model weights":    r.ModelPath,
	}
	for label, path := range checks {
		clean := filepath.Clean(path)
		info, err := os.Stat(clean)
		if err != nil {
			return fmt.Errorf("%s not available at %s: %w", label, clean, err)
		}
		if info.IsDir() {
			return fmt.Errorf("%s path is a directory: %s", label, clean)
		}
	}
	return nil
}

// Generate runs the C++ inference binary with a bounded timeout. The C++ binary
// currently prints progress text and generated tokens; the wrapper returns the
// combined output with a truth label rather than pretending to expose a polished
// model API.
func (r *Runner) Generate(parent context.Context, prompt string, maxTokens int) (*Result, error) {
	if err := r.Validate(); err != nil {
		return nil, err
	}
	if strings.TrimSpace(prompt) == "" {
		return nil, errors.New("prompt is required")
	}
	if maxTokens <= 0 {
		maxTokens = 128
	}

	ctx, cancel := context.WithTimeout(parent, r.Timeout)
	defer cancel()

	cmd := exec.CommandContext(ctx, r.BinaryPath, r.VocabPath, r.ModelPath, prompt)
	cmd.Env = append(os.Environ(), fmt.Sprintf("OVERLLM_MAX_TOKENS=%d", maxTokens))
	out, err := cmd.CombinedOutput()
	if ctx.Err() == context.DeadlineExceeded {
		return nil, fmt.Errorf("local model timed out after %s", r.Timeout)
	}
	if err != nil {
		return nil, fmt.Errorf("local model failed: %w: %s", err, strings.TrimSpace(string(out)))
	}

	return &Result{
		Text:       strings.TrimSpace(string(out)),
		Runtime:    filepath.Clean(r.BinaryPath),
		ModelPath:  filepath.Clean(r.ModelPath),
		VocabPath:  filepath.Clean(r.VocabPath),
		TruthLabel: "real_local_process_output",
	}, nil
}
