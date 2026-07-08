#!/usr/bin/env python3
"""OverLLM's own byte-level BPE tokenizer: trainer + Python encoder/decoder.

This is a real implementation of the algorithm production tokenizers use
(GPT-2/3.5/4 via tiktoken, Llama, and others all use byte-level BPE): start
from the 256 possible raw bytes as the base vocabulary, then iteratively
merge the most frequent adjacent symbol pair in a training corpus, recording
each merge in priority order. Encoding a new string applies those merges
greedily, in the order they were learned.

This is OverLLM's own tokenizer, trained on OverLLM's own text (this repo's
README/docs), not GPT-4/Claude/Llama's production tokenizer. The vocabulary
is small (a few hundred to a couple thousand merges) because the training
corpus is a few hundred KB, not internet-scale — token *counts* here measure
this tokenizer specifically, not what a production API would bill. What
makes it "actual BPE" rather than a proxy: it is the real, standard
algorithm, genuinely trained and genuinely applied, not an approximation.

Byte-level coverage means encode/decode round-trips exactly for any input,
including arbitrary Unicode, control characters, and the RSTF module's own
transform glyphs (upside-down, homoglyph, bidi-override) - there is no
<unk> fallback because every possible byte is in the base vocabulary.

This module is also mirrored in C++ (cpp/src/tokenizer.cpp), which is the
"real" build target this repo already ships; see tools/bpe_parity_check.py
for a test that the compiled C++ binary and this Python implementation
produce identical token ID sequences on the same inputs.

Usage:

  python tools/bpe_tokenizer.py train --corpus-glob "README.md" "docs/*.md" \
      --vocab-size 1500 --out-dir cpp/tokenizer_data
  python tools/bpe_tokenizer.py encode --text "hello world" --vocab-dir cpp/tokenizer_data
"""

from __future__ import annotations

import argparse
import glob
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_VOCAB_DIR = REPO_ROOT / "cpp" / "tokenizer_data"

# Deliberately NOT the exact GPT-2 pre-tokenization regex (which splits
# separately on \p{L}+ / \p{N}+ / punctuation using Unicode category regex,
# requiring the third-party `regex` package's ICU-backed \p{} support). This
# module has a real, compiled C++ mirror (cpp/src/tokenizer.cpp) with no
# Unicode-regex library available, and the whole point of that mirror is
# genuine parity with this Python implementation, not a claim of GPT-2
# fidelity. So both implementations use the same simpler, byte-scannable
# rule instead: split into whitespace runs and non-whitespace runs, with
# each non-whitespace run keeping at most one leading space attached (the
# GPT-2 convention that lets " world" and "world" merge differently, which
# matters for compression quality). ASCII whitespace bytes never appear as
# continuation bytes in valid UTF-8, so this rule is safe to implement as
# plain byte scanning in both languages, which is what makes an exact
# byte-for-byte match between the Python and C++ tokenizers checkable.


def _bytes_to_unicode() -> dict[int, str]:
    """The standard GPT-2 byte<->printable-unicode mapping (public, well-known
    algorithm from OpenAI's gpt2 encoder.py). Maps every byte value 0-255 to
    a distinct printable character so BPE can operate on byte sequences
    without hitting whitespace/control-character edge cases."""
    bs = (
        list(range(ord("!"), ord("~") + 1))
        + list(range(ord("\xa1"), ord("\xac") + 1))
        + list(range(ord("\xae"), ord("\xff") + 1))
    )
    cs = bs[:]
    n = 0
    for b in range(256):
        if b not in bs:
            bs.append(b)
            cs.append(256 + n)
            n += 1
    return dict(zip(bs, [chr(c) for c in cs]))


_BYTE_ENCODER = _bytes_to_unicode()
_BYTE_DECODER = {v: k for k, v in _BYTE_ENCODER.items()}


def _get_pairs(symbols: tuple[str, ...]) -> set[tuple[str, str]]:
    return {(symbols[i], symbols[i + 1]) for i in range(len(symbols) - 1)}


_ASCII_WHITESPACE = set(" \t\n\r\v\f")


def pretokenize(text: str) -> list[str]:
    """Split into whitespace runs and (at-most-one-leading-space)
    non-whitespace runs. See the module-level comment above _ASCII_WHITESPACE
    for why this isn't the full GPT-2 regex: it must be exactly reproducible
    as plain byte scanning in the C++ mirror, with no Unicode-regex library."""
    words: list[str] = []
    i = 0
    n = len(text)
    while i < n:
        if text[i] in _ASCII_WHITESPACE:
            j = i
            while j < n and text[j] in _ASCII_WHITESPACE:
                j += 1
            if j == n:
                # Whitespace runs to end of text: no following word to
                # attach a leading space to, so the whole run is one token.
                words.append(text[i:j])
                i = j
            else:
                # All but the last whitespace char form their own token (if
                # any remain); the last one is held back to become the
                # leading space of the following non-whitespace word.
                if j - i > 1:
                    words.append(text[i:j - 1])
                k = j
                while k < n and text[k] not in _ASCII_WHITESPACE:
                    k += 1
                words.append(text[j - 1:k])
                i = k
        else:
            j = i
            while j < n and text[j] not in _ASCII_WHITESPACE:
                j += 1
            words.append(text[i:j])
            i = j
    return [w for w in words if w]


def word_to_byte_symbols(word: str) -> tuple[str, ...]:
    return tuple(_BYTE_ENCODER[b] for b in word.encode("utf-8"))


def train_bpe(corpus: str, vocab_size: int, min_pair_freq: int = 2) -> tuple[list[tuple[str, str]], dict[str, int]]:
    """Standard BPE training (Sennrich et al. 2015): count word frequencies,
    represent each word as byte symbols, repeatedly merge the most frequent
    adjacent pair until vocab_size is reached or no pair repeats often
    enough to be worth merging."""
    word_freq: Counter[tuple[str, ...]] = Counter()
    for word in pretokenize(corpus):
        word_freq[word_to_byte_symbols(word)] += 1

    base_vocab = sorted(set(_BYTE_ENCODER.values()))
    vocab: dict[str, int] = {sym: i for i, sym in enumerate(base_vocab)}
    merges: list[tuple[str, str]] = []

    words = dict(word_freq)
    target_merges = max(0, vocab_size - len(vocab))

    for _ in range(target_merges):
        pair_counts: Counter[tuple[str, str]] = Counter()
        for symbols, freq in words.items():
            for pair in _get_pairs(symbols):
                pair_counts[pair] += freq
        if not pair_counts:
            break
        best_pair, best_count = pair_counts.most_common(1)[0]
        if best_count < min_pair_freq:
            break

        merged_symbol = best_pair[0] + best_pair[1]
        merges.append(best_pair)
        vocab[merged_symbol] = len(vocab)

        new_words: dict[tuple[str, ...], int] = {}
        for symbols, freq in words.items():
            new_symbols: list[str] = []
            i = 0
            while i < len(symbols):
                if i < len(symbols) - 1 and (symbols[i], symbols[i + 1]) == best_pair:
                    new_symbols.append(merged_symbol)
                    i += 2
                else:
                    new_symbols.append(symbols[i])
                    i += 1
            new_words[tuple(new_symbols)] = new_words.get(tuple(new_symbols), 0) + freq
        words = new_words

    return merges, vocab


class BPETokenizer:
    def __init__(self, vocab: dict[str, int], merges: list[tuple[str, str]]):
        self.vocab = vocab
        self.inverse_vocab = {v: k for k, v in vocab.items()}
        self.merge_rank = {pair: i for i, pair in enumerate(merges)}
        self._cache: dict[str, tuple[str, ...]] = {}

    @classmethod
    def load(cls, vocab_dir: Path) -> "BPETokenizer":
        vocab_path = Path(vocab_dir) / "vocab.json"
        merges_path = Path(vocab_dir) / "merges.txt"
        vocab = json.loads(vocab_path.read_text(encoding="utf-8"))
        merges: list[tuple[str, str]] = []
        for line in merges_path.read_text(encoding="utf-8").splitlines():
            if not line or line.startswith("#"):
                continue
            left, right = line.split(" ")
            merges.append((left, right))
        return cls(vocab, merges)

    def save(self, vocab_dir: Path) -> None:
        vocab_dir = Path(vocab_dir)
        vocab_dir.mkdir(parents=True, exist_ok=True)
        (vocab_dir / "vocab.json").write_text(json.dumps(self.vocab, ensure_ascii=False, indent=0), encoding="utf-8")
        # Plain tab-separated "symbol<TAB>id" export for the C++ mirror
        # (cpp/src/tokenizer.cpp), which has no JSON parser dependency.
        vocab_lines = [f"{sym}\t{idx}" for sym, idx in sorted(self.vocab.items(), key=lambda kv: kv[1])]
        (vocab_dir / "vocab.txt").write_text("\n".join(vocab_lines) + "\n", encoding="utf-8")
        merges_lines = [f"{left} {right}" for left, right in sorted(self.merge_rank, key=self.merge_rank.get)]
        (vocab_dir / "merges.txt").write_text("\n".join(merges_lines) + "\n", encoding="utf-8")

    def _bpe_word(self, symbols: tuple[str, ...]) -> tuple[str, ...]:
        if symbols in self._cache:
            return self._cache[symbols]
        working = list(symbols)
        while len(working) > 1:
            pairs = _get_pairs(tuple(working))
            ranked = [(self.merge_rank[p], p) for p in pairs if p in self.merge_rank]
            if not ranked:
                break
            _, best_pair = min(ranked)
            merged = best_pair[0] + best_pair[1]
            new_symbols: list[str] = []
            i = 0
            while i < len(working):
                if i < len(working) - 1 and (working[i], working[i + 1]) == best_pair:
                    new_symbols.append(merged)
                    i += 2
                else:
                    new_symbols.append(working[i])
                    i += 1
            working = new_symbols
        result = tuple(working)
        self._cache[symbols] = result
        return result

    def encode(self, text: str) -> list[int]:
        token_ids: list[int] = []
        for word in pretokenize(text):
            symbols = word_to_byte_symbols(word)
            for sym in self._bpe_word(symbols):
                token_ids.append(self.vocab[sym])
        return token_ids

    def decode(self, token_ids: list[int]) -> str:
        symbols = "".join(self.inverse_vocab[i] for i in token_ids)
        raw_bytes = bytes(_BYTE_DECODER[c] for c in symbols)
        return raw_bytes.decode("utf-8")


def cmd_train(args: argparse.Namespace) -> None:
    corpus_parts: list[str] = []
    for pattern in args.corpus_glob:
        for path_str in sorted(glob.glob(str(REPO_ROOT / pattern))):
            path = Path(path_str)
            if path.is_file():
                corpus_parts.append(path.read_text(encoding="utf-8", errors="ignore"))
    corpus = "\n".join(corpus_parts)
    if not corpus.strip():
        raise SystemExit("Empty training corpus - check --corpus-glob patterns")

    merges, vocab = train_bpe(corpus, args.vocab_size, args.min_pair_freq)
    tokenizer = BPETokenizer(vocab, merges)
    out_dir = Path(args.out_dir)
    tokenizer.save(out_dir)

    print(json.dumps({
        "corpus_bytes": len(corpus.encode("utf-8")),
        "corpus_files": len(corpus_parts),
        "vocab_size": len(vocab),
        "merges_learned": len(merges),
        "out_dir": str(out_dir),
    }, indent=2))


def cmd_encode(args: argparse.Namespace) -> None:
    tokenizer = BPETokenizer.load(Path(args.vocab_dir))
    ids = tokenizer.encode(args.text)
    decoded = tokenizer.decode(ids)
    print(json.dumps({
        "text": args.text,
        "token_ids": ids,
        "token_count": len(ids),
        "decoded_matches_input": decoded == args.text,
    }, indent=2, ensure_ascii=False))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="OverLLM byte-level BPE tokenizer trainer/encoder")
    sub = parser.add_subparsers(dest="command", required=True)

    train = sub.add_parser("train", help="Train a BPE vocabulary from a corpus")
    train.add_argument("--corpus-glob", nargs="+", required=True, help="Glob pattern(s) relative to repo root, e.g. 'README.md' 'docs/*.md'")
    train.add_argument("--vocab-size", type=int, default=1500)
    train.add_argument("--min-pair-freq", type=int, default=2)
    train.add_argument("--out-dir", default=str(DEFAULT_VOCAB_DIR))
    train.set_defaults(func=cmd_train)

    encode = sub.add_parser("encode", help="Encode text with a trained vocabulary")
    encode.add_argument("--text", required=True)
    encode.add_argument("--vocab-dir", default=str(DEFAULT_VOCAB_DIR))
    encode.set_defaults(func=cmd_encode)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
