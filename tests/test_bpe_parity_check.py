import pathlib
import shutil
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

from bpe_parity_check import run_parity_check

VOCAB_DIR = ROOT / "cpp" / "tokenizer_data"


@pytest.mark.skipif(shutil.which("g++") is None, reason="g++ not available")
def test_cpp_and_python_tokenizers_agree_on_all_cases():
    report = run_parity_check(VOCAB_DIR)
    assert report["status"] == "ok", report
    assert report["mismatch_count"] == 0
    assert report["case_count"] >= 10
