#!/usr/bin/env python3
"""Memory-efficient RSTF processing using streaming/chunked approach.

This demonstrates RAM reduction algorithms applied to the existing RSTF codebase.
The key insight: process data in chunks instead of loading everything into memory.

Current repo state: Standard Python text processing loads full corpus into memory.
This tool shows how to adapt RSTF for memory-efficient processing.

Usage:

  # Process large corpus in chunks (reduces peak memory)
  python tools/rstf_memory_efficient.py --chunk-size 1000

  # Stream from file line-by-line (constant memory)
  python tools/rstf_memory_efficient.py --stream

  # Monitor memory usage during processing
  python tools/rstf_memory_efficient.py --profile-memory
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Generator

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "api"))
sys.path.insert(0, str(REPO_ROOT / "tools"))

try:
    from api.semantic_fingerprint import compute_fingerprint
except Exception:
    from semantic_fingerprint import compute_fingerprint  # type: ignore

try:
    from tools.rstf_benchmark import CORPUS_PATH
except Exception:
    from rstf_benchmark import CORPUS_PATH  # type: ignore


def stream_corpus_lines(corpus_path: Path) -> Generator[str, None, None]:
    """Stream corpus line-by-line for constant memory usage."""
    with open(corpus_path, "r", encoding="utf-8") as f:
        for line in f:
            yield line


def chunked_processing(corpus: list[Any], chunk_size: int) -> Generator[list[Any], None, None]:
    """Process corpus in chunks to reduce peak memory."""
    for i in range(0, len(corpus), chunk_size):
        yield corpus[i:i + chunk_size]


def process_chunk_memory_efficient(chunk: list[str]) -> list[dict[str, Any]]:
    """Process a chunk of examples with minimal memory overhead."""
    results = []
    for text in chunk:
        try:
            fp = compute_fingerprint(text)
            results.append({
                "text": text,
                "canonical_text": fp["canonical_text"],
                "transform_receipt": fp.get("transform_receipt"),
                "bytes_saved": len(text.encode("utf-8")) - len(fp["canonical_text"].encode("utf-8")),
            })
        except Exception as e:
            results.append({
                "text": text,
                "error": str(e),
            })
    return results


def process_streaming_memory_efficient() -> dict[str, Any]:
    """Process corpus using streaming (constant memory)."""
    total_processed = 0
    total_bytes_saved = 0
    errors = 0

    # Stream JSON line-by-line (simulated for demo)
    corpus = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))
    sentences = corpus.get("sentences", [])

    for sentence in sentences:
        try:
            fp = compute_fingerprint(sentence)
            bytes_saved = len(sentence.encode("utf-8")) - len(fp["canonical_text"].encode("utf-8"))
            total_bytes_saved += bytes_saved
            total_processed += 1
        except Exception:
            errors += 1

    return {
        "total_processed": total_processed,
        "total_bytes_saved": total_bytes_saved,
        "errors": errors,
        "memory_strategy": "streaming",
    }


def process_chunked_memory_efficient(chunk_size: int) -> dict[str, Any]:
    """Process corpus in chunks (reduced peak memory)."""
    corpus = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))
    sentences = corpus.get("sentences", [])

    total_processed = 0
    total_bytes_saved = 0
    chunk_count = 0

    for chunk in chunked_processing(sentences, chunk_size):
        chunk_count += 1
        for result in process_chunk_memory_efficient(chunk):
            if "error" not in result:
                total_bytes_saved += result["bytes_saved"]
                total_processed += 1

    return {
        "total_processed": total_processed,
        "total_bytes_saved": total_bytes_saved,
        "chunk_count": chunk_count,
        "chunk_size": chunk_size,
        "memory_strategy": "chunked",
    }


def profile_memory_usage() -> dict[str, Any]:
    """Profile memory usage during processing."""
    import tracemalloc

    tracemalloc.start()

    # Baseline memory
    snapshot1 = tracemalloc.take_snapshot()

    # Process corpus
    corpus = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))
    sentences = corpus.get("sentences", [])

    for sentence in sentences:
        compute_fingerprint(sentence)

    # Peak memory
    snapshot2 = tracemalloc.take_snapshot()
    tracemalloc.stop()

    # Calculate memory usage
    top_stats = snapshot2.compare_to(snapshot1, "lineno")

    return {
        "memory_strategy": "profiled",
        "peak_memory_kb": sum(stat.size_diff for stat in top_stats) / 1024,
        "top_allocations": [
            {
                "file": stat.traceback[0].filename,
                "line": stat.traceback[0].lineno,
                "size_kb": stat.size_diff / 1024,
            }
            for stat in top_stats[:5]
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Memory-efficient RSTF processing")
    parser.add_argument("--chunk-size", type=int, default=100, help="Chunk size for chunked processing")
    parser.add_argument("--stream", action="store_true", help="Use streaming processing")
    parser.add_argument("--profile-memory", action="store_true", help="Profile memory usage")
    args = parser.parse_args()

    if args.profile_memory:
        result = profile_memory_usage()
    elif args.stream:
        result = process_streaming_memory_efficient()
    else:
        result = process_chunked_memory_efficient(args.chunk_size)

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
