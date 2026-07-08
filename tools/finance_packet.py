#!/usr/bin/env python3
"""Generate financeable evidence packets for OverLLM.

Examples:

  python tools/finance_packet.py receipt \
    --source local.agent \
    --work-unit demo-deliverable \
    --prompt-text "build a signed receipt ledger" \
    --output-file api/financeable.py \
    --amount-usd 500

  python tools/finance_packet.py revenue \
    --event-type pilot \
    --amount-usd 500 \
    --memo "Paid pilot for receipt ledger"

  python tools/finance_packet.py report --title "OverLLM diligence packet"
  python tools/finance_packet.py summary

The CLI writes to OVERLLM_FINANCE_ROOT, default `.overllm/finance`.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "api"))

try:
    from api.financeable import (
        RECEIPTS_PATH,
        REVENUE_PATH,
        REPORTS_PATH,
        _append_record,
        _hash_payload,
        build_finance_summary,
    )
except Exception:
    from financeable import (  # type: ignore
        RECEIPTS_PATH,
        REVENUE_PATH,
        REPORTS_PATH,
        _append_record,
        _hash_payload,
        build_finance_summary,
    )


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))


def print_json(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


def cmd_receipt(args: argparse.Namespace) -> None:
    prompt_hash = args.prompt_hash or sha256_text(args.prompt_text or "")
    if args.output_hash:
        output_hash = args.output_hash
    elif args.output_file:
        output_path = Path(args.output_file)
        if not output_path.exists():
            raise SystemExit(f"output file does not exist: {output_path}")
        output_hash = sha256_bytes(output_path.read_bytes())
    else:
        output_hash = sha256_text(args.output_text or "")

    payload = {
        "source": args.source,
        "work_unit": args.work_unit,
        "prompt_hash": prompt_hash,
        "output_hash": output_hash,
        "runtime": args.runtime,
        "truth_label": args.truth_label,
        "customer_hash": args.customer_hash,
        "contract_ref_hash": args.contract_ref_hash,
        "amount_usd": args.amount_usd,
        "tags": args.tag or [],
        "metadata": {
            "output_file": args.output_file,
            "cli": "tools/finance_packet.py receipt",
        },
    }
    payload["payload_hash"] = _hash_payload(payload)
    print_json(_append_record(RECEIPTS_PATH, "work_receipt", payload))


def cmd_revenue(args: argparse.Namespace) -> None:
    payload = {
        "event_type": args.event_type,
        "amount_usd": args.amount_usd,
        "payer_hash": args.payer_hash,
        "receipt_id": args.receipt_id,
        "contract_ref_hash": args.contract_ref_hash,
        "memo": args.memo,
        "recurring": args.recurring,
        "metadata": {"cli": "tools/finance_packet.py revenue"},
    }
    payload["payload_hash"] = _hash_payload(payload)
    print_json(_append_record(REVENUE_PATH, "revenue_event", payload))


def cmd_report(args: argparse.Namespace) -> None:
    summary = build_finance_summary()
    payload = {
        "title": args.title,
        "scope": args.scope,
        "narrative": args.narrative,
        "requested_amount_usd": args.requested_amount_usd,
        "summary": summary,
        "metadata": {"cli": "tools/finance_packet.py report"},
    }
    payload["payload_hash"] = _hash_payload(payload)
    print_json(_append_record(REPORTS_PATH, "collateral_report", payload))


def cmd_summary(_args: argparse.Namespace) -> None:
    print_json(build_finance_summary())


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="OverLLM financeable evidence packet CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    receipt = sub.add_parser("receipt", help="Create a tamper-evident work receipt")
    receipt.add_argument("--source", required=True)
    receipt.add_argument("--work-unit", required=True)
    receipt.add_argument("--runtime", default="overllm")
    receipt.add_argument("--truth-label", default="experimental", choices=["real", "experimental", "partial", "not_configured"])
    receipt.add_argument("--prompt-text", default="")
    receipt.add_argument("--prompt-hash")
    receipt.add_argument("--output-text", default="")
    receipt.add_argument("--output-file")
    receipt.add_argument("--output-hash")
    receipt.add_argument("--amount-usd", type=float)
    receipt.add_argument("--customer-hash")
    receipt.add_argument("--contract-ref-hash")
    receipt.add_argument("--tag", action="append")
    receipt.set_defaults(func=cmd_receipt)

    revenue = sub.add_parser("revenue", help="Create a revenue event")
    revenue.add_argument("--event-type", required=True, choices=["invoice", "subscription", "license", "usage", "consulting", "grant", "pilot", "other"])
    revenue.add_argument("--amount-usd", required=True, type=float)
    revenue.add_argument("--payer-hash")
    revenue.add_argument("--receipt-id")
    revenue.add_argument("--contract-ref-hash")
    revenue.add_argument("--memo", default="")
    revenue.add_argument("--recurring", action="store_true")
    revenue.set_defaults(func=cmd_revenue)

    report = sub.add_parser("report", help="Create a collateral/diligence report from the local ledger")
    report.add_argument("--title", default="OverLLM Financeable Evidence Packet")
    report.add_argument("--scope", default="repository", choices=["repository", "customer", "pilot", "grant", "sale", "internal"])
    report.add_argument("--narrative", default="")
    report.add_argument("--requested-amount-usd", type=float)
    report.set_defaults(func=cmd_report)

    summary = sub.add_parser("summary", help="Print financeable ledger summary")
    summary.set_defaults(func=cmd_summary)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
