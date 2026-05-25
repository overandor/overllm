#!/bin/bash
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "=== OverLLM Build System ==="
echo "Building C++ inference engine + Go agent + Rust telemetry daemon"
echo ""

# --- C++ ---
echo "[1/3] Building C++ inference engine..."
cd "$DIR/cpp"
mkdir -p build lib
if [ ! -f build/Makefile ]; then
    cmake -B build -S . -DCMAKE_BUILD_TYPE=Release
fi
cmake --build build -j$(sysctl -n hw.ncpu)
cp build/liboverllm.dylib "$DIR/lib/" 2>/dev/null || cp build/liboverllm.so "$DIR/lib/" 2>/dev/null || true
cp build/overllm_inference "$DIR/" 2>/dev/null || true
echo "C++ OK"
echo ""

# --- Go ---
echo "[2/3] Building Go agent..."
cd "$DIR/go"
export CGO_ENABLED=1
export CGO_CFLAGS="-I$DIR/cpp/include"
export CGO_LDFLAGS="-L$DIR/lib -loverllm -Wl,-rpath,$DIR/lib"
export DYLD_LIBRARY_PATH="$DIR/lib:$DYLD_LIBRARY_PATH"
go mod tidy 2>/dev/null || true
go build -o "$DIR/overllm-agent" ./cmd/overllm-agent
echo "Go OK"
echo ""

# --- Rust ---
echo "[3/3] Building Rust telemetry daemon..."
cd "$DIR/rust"
cargo build --release
cp target/release/overllm-telemetry "$DIR/"
echo "Rust OK"
echo ""

echo "=== BUILD COMPLETE ==="
echo "Binaries:"
echo "  ./overllm-agent      - Go orchestrator + Ollama integration + HTTP API"
echo "  ./overllm-telemetry  - Rust system context collector"
echo "  ./overllm_inference  - C++ standalone inference tool"
echo "  ./lib/liboverllm.*   - C++ shared library"
echo ""
echo "Quick start:"
echo "  1. Ensure Ollama is running: ollama serve"
echo "  2. Start agent:    ./overllm-agent"
echo "  3. Start telemetry: ./overllm-telemetry"
echo "  4. Generate data: python training/generate.py --count 20"
echo "  5. Train model:   python training/dpo_trainer.py --epochs 10"
