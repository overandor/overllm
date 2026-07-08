from __future__ import annotations

from tools import rstf_real_corpus_cost as real_cost


def test_real_corpus_scan_clean_text_has_zero_prevalence():
    records = [
        real_cost.TextRecord(source_id="clean:1", text="This is a normal support message."),
        real_cost.TextRecord(source_id="clean:2", text="Another ordinary line with no transform."),
    ]

    report = real_cost.scan_records(
        records=records,
        tokenizer="bytes",
        model=None,
        encoding_name="cl100k_base",
        include_examples=True,
        compressor="zlib",
    )

    assert report["overall"]["records_scanned"] == 2
    assert report["overall"]["records_with_transform_detected"] == 0
    assert report["overall"]["transform_prevalence_ratio"] == 0.0
    assert report["examples"] == []
    assert report["ram_compression"]["compressor"] == "zlib_level_6"
    assert report["ram_compression"]["truth_label"] == real_cost.COMPRESSION_TRUTH_LABEL


def test_real_corpus_scan_detects_actual_transformed_input():
    records = [
        real_cost.TextRecord(source_id="realish:1", text="ʇsǝʇ ǝƃɐssǝɯ"),
        real_cost.TextRecord(source_id="realish:2", text="This is ordinary."),
    ]

    report = real_cost.scan_records(
        records=records,
        tokenizer="bytes",
        model=None,
        encoding_name="cl100k_base",
        include_examples=True,
        compressor="zlib",
    )

    assert report["overall"]["records_scanned"] == 2
    assert report["overall"]["records_with_transform_detected"] == 1
    assert "upside_down" in report["per_transform"]
    assert len(report["examples"]) == 1
    assert report["truth_label"] == real_cost.REPORT_TRUTH_LABEL
    assert "compressed_raw_bytes" in report["examples"][0]


def test_ram_compression_metrics_include_hot_and_audit_paths():
    report = real_cost.scan_records(
        records=[real_cost.TextRecord(source_id="x", text="ʇsǝʇ ǝƃɐssǝɯ")],
        tokenizer="bytes",
        model=None,
        encoding_name="cl100k_base",
        include_examples=True,
        compressor="zlib",
    )
    ram = report["ram_compression"]

    assert ram["raw_utf8_bytes"] > 0
    assert ram["canonical_utf8_bytes"] > 0
    assert ram["receipt_json_bytes"] > 0
    assert ram["compressed_raw_bytes"] > 0
    assert ram["compressed_canonical_bytes"] > 0
    assert ram["compressed_canonical_plus_receipt_bytes"] > 0
    assert ram["hot_path_policy"] == "canonical_text_only"
    assert ram["audit_path_policy"] == "canonical_text_plus_compact_receipt_raw_text_cold_storage_if_required"


def test_jsonl_reader_uses_text_field_and_id(tmp_path):
    path = tmp_path / "records.jsonl"
    path.write_text('{"id":"a1","message":"hello"}\n{"id":"a2","message":"world"}\n', encoding="utf-8")

    records = list(real_cost.iter_jsonl_file(path, text_field="message"))

    assert [r.source_id for r in records] == ["a1", "a2"]
    assert [r.text for r in records] == ["hello", "world"]


def test_markdown_documents_real_input_scope_and_ram_metrics():
    report = real_cost.scan_records(
        records=[real_cost.TextRecord(source_id="x", text="This is clean.")],
        tokenizer="bytes",
        model=None,
        encoding_name="cl100k_base",
        include_examples=False,
        compressor="zlib",
    )
    markdown = real_cost.render_markdown(report)

    assert "Real Corpus" in markdown
    assert "does not generate attack examples" in markdown
    assert "RAM compression A/B" in markdown
    assert real_cost.REPORT_TRUTH_LABEL in markdown
