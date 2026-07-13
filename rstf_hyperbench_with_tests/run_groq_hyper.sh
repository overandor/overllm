#!/usr/bin/env bash
set -euo pipefail

python rstf_hyperbench.py \
  --provider groq \
  --models "${MODELS:-llama-3.1-8b-instant,llama-3.3-70b-versatile}" \
  --n-per-transform "${N_PER_TRANSFORM:-100}" \
  --repeats "${REPEATS:-1}" \
  --out-dir "results/groq_hyper_${N_PER_TRANSFORM:-100}x${REPEATS:-1}" \
  --sleep "${SLEEP:-0.15}"
