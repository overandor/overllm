// Package localmodel shells out to OverLLM's compiled C++ inference engine
// (cpp/src/inference_main.cpp) rather than reimplementing inference in Go.
// The model itself lives in C++; this package's only job is invoking the
// binary, validating its inputs exist, and parsing its stdout.
package localmodel

import (
	"bytes"
	"context"
	"fmt"
	"os"
	"os/exec"
	"strconv"
	"strings"
	"syscall"
	"time"
)

const (
	envBinaryPath = "OVERLLM_INFERENCE_BINARY"
	envModelPath  = "OVERLLM_MODEL_PATH"
	envVocabPath  = "OVERLLM_VOCAB_PATH"
	envTimeout    = "OVERLLM_INFERENCE_TIMEOUT_SECS"

	defaultBinaryPath = "./overllm_inference"
	defaultModelPath  = "models/overllm.bin"
	defaultVocabPath  = "vocab.txt"
	defaultTimeout    = 30 * time.Second
)

// Runner points at one inference binary/model/vocab triple and the timeout
// to run it under.
type Runner struct {
	BinaryPath string
	ModelPath  string
	VocabPath  string
	Timeout    time.Duration
}

// NewFromEnv builds a Runner from OVERLLM_* environment variables, falling
// back to the paths the repo's build.sh / README quick start produce
// (./overllm_inference, models/overllm.bin, vocab.txt), then validates it.
//
// It returns (nil, err) if the runtime isn't actually usable yet — e.g. the
// model hasn't been trained/exported, or the binary hasn't been built —
// rather than returning a Runner that will fail on first use. Callers treat
// a nil Runner as "local model unavailable" and degrade gracefully (see
// server.Server.Model's nil-checks), which is the whole point: on a fresh
// checkout with nothing trained yet, the server should still start.
func NewFromEnv() (*Runner, error) {
	r := &Runner{
		BinaryPath: envOr(envBinaryPath, defaultBinaryPath),
		ModelPath:  envOr(envModelPath, defaultModelPath),
		VocabPath:  envOr(envVocabPath, defaultVocabPath),
		Timeout:    defaultTimeout,
	}
	if v := os.Getenv(envTimeout); v != "" {
		if secs, err := strconv.Atoi(v); err == nil && secs > 0 {
			r.Timeout = time.Duration(secs) * time.Second
		}
	}
	if err := r.Validate(); err != nil {
		return nil, err
	}
	return r, nil
}

func envOr(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}

// Validate checks that the binary, model, and vocab this Runner points at
// still exist and that the binary is executable. It re-checks the
// filesystem on every call rather than caching a one-time result, so a
// model trained after the server started is picked up without a restart.
func (r *Runner) Validate() error {
	info, err := os.Stat(r.BinaryPath)
	if err != nil {
		return fmt.Errorf("inference binary not found at %q: %w", r.BinaryPath, err)
	}
	if info.Mode()&0111 == 0 {
		return fmt.Errorf("inference binary at %q is not executable", r.BinaryPath)
	}
	if _, err := os.Stat(r.ModelPath); err != nil {
		return fmt.Errorf("model weights not found at %q: %w", r.ModelPath, err)
	}
	if _, err := os.Stat(r.VocabPath); err != nil {
		return fmt.Errorf("vocab file not found at %q: %w", r.VocabPath, err)
	}
	return nil
}

// Result is the outcome of one Generate call.
type Result struct {
	Text       string `json:"text"`
	DurationMs int64  `json:"duration_ms"`
	Runtime    string `json:"runtime"`
}

// Generate shells out to the inference binary as
// `<binary> <vocab> <model> <prompt>` — matching the argv contract in
// cpp/src/inference_main.cpp — and extracts the generated continuation from
// its stdout.
//
// maxTokens is accepted for API-shape stability with future runtimes, but
// the current C++ engine always generates a fixed 50-token budget; it does
// not yet take a token-count argument. That is a real limitation of the C++
// engine itself (see cpp/src/inference_main.cpp), not something this
// wrapper can paper over, so it is not silently pretended away here.
func (r *Runner) Generate(ctx context.Context, prompt string, maxTokens int) (*Result, error) {
	if err := r.Validate(); err != nil {
		return nil, err
	}
	runCtx, cancel := context.WithTimeout(ctx, r.Timeout)
	defer cancel()

	start := time.Now()
	cmd := exec.CommandContext(runCtx, r.BinaryPath, r.VocabPath, r.ModelPath, prompt)
	var stdout, stderr bytes.Buffer
	cmd.Stdout = &stdout
	cmd.Stderr = &stderr
	// Run the inference process in its own process group and, on timeout,
	// kill the whole group rather than just the direct child. Otherwise a
	// killed process's own children can survive as orphans still holding
	// the stdout/stderr pipes open, and cmd.Wait() below would hang past
	// the timeout waiting for those pipes to see EOF.
	cmd.SysProcAttr = &syscall.SysProcAttr{Setpgid: true}
	cmd.Cancel = func() error {
		return syscall.Kill(-cmd.Process.Pid, syscall.SIGKILL)
	}
	runErr := cmd.Run()
	duration := time.Since(start)

	if runCtx.Err() == context.DeadlineExceeded {
		return nil, fmt.Errorf("inference timed out after %s", r.Timeout)
	}
	if runErr != nil {
		return nil, fmt.Errorf("inference process failed: %w (stderr: %s)", runErr, strings.TrimSpace(stderr.String()))
	}

	text, err := parseGeneratedText(stdout.String())
	if err != nil {
		return nil, err
	}
	return &Result{
		Text:       text,
		DurationMs: duration.Milliseconds(),
		Runtime:    r.BinaryPath,
	}, nil
}

// parseGeneratedText strips inference_main.cpp's diagnostic prints ("Loaded
// vocab: N tokens", "Prompt: ...", "Generating...") and returns just the
// generated continuation that follows the "Generating..." line.
func parseGeneratedText(stdout string) (string, error) {
	const marker = "Generating...\n"
	idx := strings.Index(stdout, marker)
	if idx == -1 {
		return "", fmt.Errorf("could not find generation output in inference stdout: %q", stdout)
	}
	return strings.TrimSpace(stdout[idx+len(marker):]), nil
}
