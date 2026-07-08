import pathlib
import shutil
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

from transformer_learning_check import check_report, compile_trainer, run_training


@pytest.mark.skipif(shutil.which("g++") is None, reason="g++ not available")
def test_real_training_loss_decreases_with_no_nan(tmp_path):
    # A fast, CI-safe configuration (~3s of training). The committed
    # benchmark/transformer_learning/report.json uses a larger run (30
    # epochs, full 6-sentence corpus) for the documented result; this test
    # only needs to prove the mechanism works, not reproduce that exact run.
    binary_path = compile_trainer(tmp_path)
    report = run_training(binary_path, epochs=6, context_window=12, sentence_limit=2)
    problems = check_report(report)
    assert not problems, problems
    assert report["epoch_losses"][-1] < report["epoch_losses"][0]


@pytest.mark.skipif(shutil.which("g++") is None, reason="g++ not available")
def test_loss_decreases_monotonically_on_fast_config(tmp_path):
    # With gradient clipping, this small/fast configuration should be
    # smoothly monotonic (no NaN-driven or exploding-gradient reversals).
    binary_path = compile_trainer(tmp_path)
    report = run_training(binary_path, epochs=6, context_window=12, sentence_limit=2)
    losses = report["epoch_losses"]
    for earlier, later in zip(losses, losses[1:]):
        assert later <= earlier + 1e-3, losses
