package localmodel

import (
	"context"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"
)

// writeFakeBinary writes a shell script that mimics inference_main.cpp's
// stdout shape (vocab-load line, prompt/generating banner, then the
// "generated" tokens), so Generate()'s output parsing can be tested without
// the real C++ engine, which this environment can't compile.
func writeFakeBinary(t *testing.T, dir string, body string) string {
	t.Helper()
	path := filepath.Join(dir, "fake_inference")
	script := "#!/bin/sh\n" + body + "\n"
	if err := os.WriteFile(path, []byte(script), 0o755); err != nil {
		t.Fatalf("write fake binary: %v", err)
	}
	return path
}

func writeFile(t *testing.T, dir, name, contents string) string {
	t.Helper()
	path := filepath.Join(dir, name)
	if err := os.WriteFile(path, []byte(contents), 0o644); err != nil {
		t.Fatalf("write %s: %v", name, err)
	}
	return path
}

func TestValidate_MissingFilesIsAnError(t *testing.T) {
	r := &Runner{
		BinaryPath: "/nonexistent/binary",
		ModelPath:  "/nonexistent/model.bin",
		VocabPath:  "/nonexistent/vocab.txt",
		Timeout:    time.Second,
	}
	if err := r.Validate(); err == nil {
		t.Fatal("expected an error for missing binary/model/vocab, got nil")
	}
}

func TestValidate_NonExecutableBinaryIsAnError(t *testing.T) {
	dir := t.TempDir()
	binPath := filepath.Join(dir, "not_executable")
	if err := os.WriteFile(binPath, []byte("not a real binary"), 0o644); err != nil {
		t.Fatal(err)
	}
	model := writeFile(t, dir, "model.bin", "weights")
	vocab := writeFile(t, dir, "vocab.txt", "<pad>\n<unk>\n")
	r := &Runner{BinaryPath: binPath, ModelPath: model, VocabPath: vocab, Timeout: time.Second}
	if err := r.Validate(); err == nil {
		t.Fatal("expected an error for a non-executable binary, got nil")
	}
}

func TestNewFromEnv_ReturnsNilRunnerWhenUnavailable(t *testing.T) {
	dir := t.TempDir()
	t.Setenv(envBinaryPath, filepath.Join(dir, "does-not-exist"))
	t.Setenv(envModelPath, filepath.Join(dir, "does-not-exist.bin"))
	t.Setenv(envVocabPath, filepath.Join(dir, "does-not-exist-vocab.txt"))

	r, err := NewFromEnv()
	if err == nil {
		t.Fatal("expected an error when the runtime is unavailable")
	}
	if r != nil {
		t.Fatalf("expected a nil Runner on failure so callers can treat it as unavailable, got %+v", r)
	}
}

func TestGenerate_ParsesGeneratedTextFromRealisticOutput(t *testing.T) {
	dir := t.TempDir()
	// Mirrors cpp/src/inference_main.cpp's exact stdout shape.
	binPath := writeFakeBinary(t, dir, `
printf 'Loaded vocab: 42 tokens\n'
printf 'Prompt: %s\nGenerating...\n' "$3"
printf 'the quick brown fox jumps \n'
`)
	model := writeFile(t, dir, "model.bin", "weights")
	vocab := writeFile(t, dir, "vocab.txt", "<pad>\n<unk>\n")

	r := &Runner{BinaryPath: binPath, ModelPath: model, VocabPath: vocab, Timeout: 5 * time.Second}
	result, err := r.Generate(context.Background(), "hello world", 50)
	if err != nil {
		t.Fatalf("Generate returned an error: %v", err)
	}
	if result.Text != "the quick brown fox jumps" {
		t.Fatalf("expected only the generated continuation, got %q", result.Text)
	}
	if result.Runtime != binPath {
		t.Fatalf("expected Runtime to record the binary path, got %q", result.Runtime)
	}
}

func TestGenerate_MissingMarkerIsAnError(t *testing.T) {
	dir := t.TempDir()
	binPath := writeFakeBinary(t, dir, `printf 'garbage output with no marker\n'`)
	model := writeFile(t, dir, "model.bin", "weights")
	vocab := writeFile(t, dir, "vocab.txt", "<pad>\n")

	r := &Runner{BinaryPath: binPath, ModelPath: model, VocabPath: vocab, Timeout: 5 * time.Second}
	if _, err := r.Generate(context.Background(), "hi", 50); err == nil {
		t.Fatal("expected an error when stdout doesn't match the expected shape")
	}
}

func TestGenerate_RespectsTimeout(t *testing.T) {
	dir := t.TempDir()
	binPath := writeFakeBinary(t, dir, `sleep 5`)
	model := writeFile(t, dir, "model.bin", "weights")
	vocab := writeFile(t, dir, "vocab.txt", "<pad>\n")

	r := &Runner{BinaryPath: binPath, ModelPath: model, VocabPath: vocab, Timeout: 100 * time.Millisecond}
	start := time.Now()
	_, err := r.Generate(context.Background(), "hi", 50)
	elapsed := time.Since(start)

	if err == nil {
		t.Fatal("expected a timeout error")
	}
	if !strings.Contains(err.Error(), "timed out") {
		t.Fatalf("expected a timeout error, got: %v", err)
	}
	if elapsed > 2*time.Second {
		t.Fatalf("Generate took %s, expected it to be cut short by the 100ms timeout", elapsed)
	}
}

func TestGenerate_PropagatesProcessFailure(t *testing.T) {
	dir := t.TempDir()
	binPath := writeFakeBinary(t, dir, `echo "boom" >&2; exit 1`)
	model := writeFile(t, dir, "model.bin", "weights")
	vocab := writeFile(t, dir, "vocab.txt", "<pad>\n")

	r := &Runner{BinaryPath: binPath, ModelPath: model, VocabPath: vocab, Timeout: 5 * time.Second}
	_, err := r.Generate(context.Background(), "hi", 50)
	if err == nil {
		t.Fatal("expected an error when the inference process exits non-zero")
	}
	if !strings.Contains(err.Error(), "boom") {
		t.Fatalf("expected the error to include stderr output, got: %v", err)
	}
}
