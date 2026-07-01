#!/usr/bin/env python3
"""
Run the OverGPT value-packet proof chain.

This script generates:

- a value packet JSON file
- an enterprise diligence report JSON file

Run:
    python3 tools/run_overgpt_quality_gate.py

Optional:
    python3 tools/run_overgpt_quality_gate.py --out-dir receipts/overgpt-demo
"""

from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import sys
from datetime import datetime, timezone
from typing import Any, Dict


ROOT = pathlib.Path(__file__).resolve().parents[1]
VALUE_PACKET = ROOT / "tools" / "value_packet_demo.py"
DILIGENCE_GATE = ROOT / "tools" / "overgpt_diligence_gate.py"


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def run_json(command: list[str]) -> Dict[str, Any]:
    completed = subprocess.run(command, check=True, capture_output=True, text=True)
    return json.loads(completed.stdout)


def write_json(path: pathlib.Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the OverGPT value-packet proof chain.")
    parser.add_argument("--out-dir", default="receipts/overgpt-demo")
    parser.add_argument("--target-valuation-usd", type=float, default=3_000_000.0)
    parser.add_argument("--stake-usd", type=float, default=100.0)
    parser.add_argument("--claimed-value-usd", type=float, default=1000.0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    out_dir = ROOT / args.out_dir
    stamp = utc_stamp()

    value_packet_path = out_dir / f"value_packet_{stamp}.json"
    diligence_report_path = out_dir / f"diligence_report_{stamp}.json"
    manifest_path = out_dir / f"manifest_{stamp}.json"

    packet = run_json(
        [
            sys.executable,
            str(VALUE_PACKET),
            "--stake-usd",
            str(args.stake_usd),
            "--claimed-value-usd",
            str(args.claimed_value_usd),
        ]
    )
    write_json(value_packet_path, packet)

    report = run_json(
        [
            sys.executable,
            str(DILIGENCE_GATE),
            str(value_packet_path),
            "--target-valuation-usd",
            str(args.target_valuation_usd),
        ]
    )
    write_json(diligence_report_path, report)

    manifest = {
        "schema": "overgpt.quality_gate_manifest.v1",
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "value_packet_path": str(value_packet_path.relative_to(ROOT)),
        "diligence_report_path": str(diligence_report_path.relative_to(ROOT)),
        "target_valuation_usd": args.target_valuation_usd,
        "enterprise_score": report.get("enterprise_score"),
        "readiness_label": report.get("readiness_label"),
        "evidence_based_valuation_ceiling_usd": report.get("evidence_based_valuation_ceiling_usd"),
        "claim_limit": report.get("claim_limit"),
    }
    write_json(manifest_path, manifest)

    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
