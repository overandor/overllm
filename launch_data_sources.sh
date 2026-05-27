#!/bin/bash
set -e

echo "=== OverLLM Data Source Launcher ==="
echo ""

DATA_DIR="$HOME/.overllm/data"
mkdir -p "$DATA_DIR"

# 1. Generate more DPO preference pairs from Ollama
echo "[1/3] Generating DPO preference pairs via Ollama..."
if curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then
  python3 training/generate.py --count 100 &
  GEN_PID=$!
  echo "  Ollama generator started (PID $GEN_PID)"
else
  echo "  Ollama not running — skipping preference generation"
  echo "  Start Ollama with: ollama serve"
fi

# 2. Fetch HuggingFace datasets
echo "[2/3] Fetching HuggingFace + News data..."
if command -v pip3 >/dev/null && python3 -c "import datasets" 2>/dev/null; then
  cd data_ingestion && python3 hf_data_fetcher.py &
  HF_PID=$!
  echo "  HuggingFace fetcher started (PID $HF_PID)"
  cd ..
else
  echo "  Install deps first: pip3 install -r data_ingestion/requirements.txt"
fi

# 3. Convert any raw text data into preference pairs
echo "[3/3] Converting raw data to DPO pairs..."
python3 -c "
import json, os, glob, time
data_dir = os.path.expanduser('~/.overllm/data')
ingested = glob.glob('data_ingestion/data/*.jsonl')
pairs_file = os.path.join(data_dir, 'preferences.jsonl')
count = 0
for fpath in ingested:
    with open(fpath) as f:
        for line in f:
            if not line.strip(): continue
            item = json.loads(line)
            text = item.get('text', '')
            if len(text) < 100: continue
            # Create synthetic preference: text with context > without
            chosen = text[:500]
            rejected = text[:200]  # Shorter = less informative = rejected
            pair = {
                'prompt': 'Provide detailed information.',
                'chosen': chosen,
                'rejected': rejected,
                'context': item.get('source', 'huggingface'),
                'timestamp': int(time.time())
            }
            with open(pairs_file, 'a') as out:
                out.write(json.dumps(pair) + '\n')
            count += 1
            if count >= 500: break
    if count >= 500: break
print(f'  Added {count} synthetic pairs from ingested data')
" 2>/dev/null || echo "  No ingested data to convert yet"

# Summary
TOTAL=$(wc -l < "$DATA_DIR/preferences.jsonl" 2>/dev/null || echo 0)
echo ""
echo "=== Data Sources Summary ==="
echo "  Total preference pairs: $TOTAL"
echo "  Data directory: $DATA_DIR"
echo ""
echo "To train: python3 training/dpo_trainer.py --data $DATA_DIR/preferences.jsonl --epochs 50 --export models/overllm.bin"
