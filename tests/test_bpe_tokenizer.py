import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

from bpe_tokenizer import BPETokenizer, pretokenize, train_bpe

VOCAB_DIR = ROOT / "cpp" / "tokenizer_data"


def test_pretokenize_reconstructs_exactly():
    cases = ["hello world", "a  b", "hi  ", " hello", "a\tb\nc", "", "   ", "a b c d"]
    for text in cases:
        assert "".join(pretokenize(text)) == text, text


def test_pretokenize_never_infinite_loops_on_repeated_single_spaces():
    # Regression guard for a real bug hit during development: a single-space
    # run previously failed to advance the scan position.
    text = "a b c d e f g"
    words = pretokenize(text)
    assert "".join(words) == text
    assert len(words) < 100  # sanity bound, would never terminate if buggy


def test_trained_tokenizer_round_trips_plain_and_transformed_text():
    tokenizer = BPETokenizer.load(VOCAB_DIR)
    cases = [
        "hello world",
        "the pull request is ready for review",
        "ʇsǝʇ",
        "аpple.com",
        "invoice‮exe.gpj‬",
        "καλημέρα σας",
        "",
        "MiXeD CaSe 123 !!!",
    ]
    for text in cases:
        ids = tokenizer.encode(text)
        assert tokenizer.decode(ids) == text, text


def test_base_vocabulary_covers_all_256_bytes():
    # Byte-level BPE guarantees full coverage: every possible byte value has
    # a base symbol, so there is never an <unk> fallback.
    tokenizer = BPETokenizer.load(VOCAB_DIR)
    all_bytes = bytes(range(256)).decode("latin-1")
    # Round-trip through raw bytes rather than decode/encode as UTF-8 text,
    # since arbitrary latin-1 isn't valid UTF-8; check base symbol coverage
    # directly instead.
    from bpe_tokenizer import _BYTE_ENCODER
    for b in range(256):
        assert _BYTE_ENCODER[b] in tokenizer.vocab, b


def test_train_bpe_is_deterministic():
    corpus = "the quick brown fox jumps over the lazy dog. " * 20
    merges_a, vocab_a = train_bpe(corpus, vocab_size=300)
    merges_b, vocab_b = train_bpe(corpus, vocab_size=300)
    assert merges_a == merges_b
    assert vocab_a == vocab_b


def test_reversed_text_costs_more_tokens_than_canonical():
    # The real finding that motivated this module: unlike UTF-8 byte length
    # (which cannot change under reordering), BPE token count is
    # order-dependent, because merges are learned from forward-reading
    # corpus text. Reversed text breaks those learned merges.
    tokenizer = BPETokenizer.load(VOCAB_DIR)
    original = "the pull request is ready for review"
    reversed_text = original[::-1]
    assert len(tokenizer.encode(reversed_text)) > len(tokenizer.encode(original))
