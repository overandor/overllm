"""Financeable evidence ledger for OverLLM.

This module turns OverLLM activity into diligence-grade records:
- signed/tamper-evident work receipts
- revenue events linked to receipts
- lender/investor-facing summary metrics
- CSV exports for underwriting, grant review, or buyer diligence

It does not invent valuation, profit, or collateral. It records evidence that can
support those conversations when paired with real customers, invoices, contracts,
and reproducible receipts.
"""

from __future__ import annotations

import csv
import hashlib
import hmac
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, validator

router = APIRouter(prefix="/finance", tags=["financeable-evidence"])

LEDGER_VERSION = "FEL-1"
FINANCE_ROOT = Path(os.getenv("OVERLLM_FINANCE_ROOT", ".overllm/finance")).resolve()
RECEIPTS_PATH = FINANCE_ROOT / "receipts.jsonl"
REVENUE_PATH = FINANCE_ROOT / "revenue_events.jsonl"
REPORTS_PATH = FINANCE_ROOT / "collateral_reports.jsonl"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _ensure_root() -> None:
    FINANCE_ROOT.mkdir(parents=True, exist_ok=True)


def _canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _hash_payload(payload: dict[str, Any]) -> str:
    return _sha256_text(_canonical_json(payload))


def _ledger_secret() -> str:
    return os.getenv("OVERLLM_LEDGER_SECRET", "")


def _sign(record_hash: str) -> dict[str, str]:
    secret = _ledger_secret()
    if not secret:
        return {
            "signature_status": "unsigned_local_hash",
            "signature": "",
            "signature_algorithm": "none",
            "signature_note": "Set OVERLLM_LEDGER_SECRET to generate HMAC-SHA256 signatures.",
        }
    signature = hmac.new(secret.encode("utf-8"), record_hash.encode("utf-8"), hashlib.sha256).hexdigest()
    return {
        "signature_status": "signed",
        "signature": signature,
        "signature_algorithm": "HMAC-SHA256",
        "signature_note": "Verify with the same OVERLLM_LEDGER_SECRET in the private diligence environment.",
    }


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                records.append({"record_type": "corrupt_line", "truth_label": "corrupt", "raw_hash": _sha256_text(line)})
    return records


def _last_hash(path: Path) -> str:
    records = _read_jsonl(path)
    for record in reversed(records):
        if isinstance(record, dict) and record.get("record_hash"):
            return str(record["record_hash"])
    return "genesis"


def _append_record(path: Path, record_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    _ensure_root()
    previous_hash = _last_hash(path)
    envelope = {
        "ledger_version": LEDGER_VERSION,
        "record_type": record_type,
        "created_at": _utc_now(),
        "previous_hash": previous_hash,
        "payload": payload,
    }
    record_hash = _hash_payload(envelope)
    envelope["record_hash"] = record_hash
    envelope.update(_sign(record_hash))
    with path.open("a", encoding="utf-8") as handle:
        handle.write(_canonical_json(envelope) + "\n")
    return envelope


class WorkReceiptInput(BaseModel):
    source: str = Field(..., description="System or surface that produced the work, e.g. api.generate, local.agent, ci, customer.demo")
    work_unit: str = Field(..., description="Human-readable work unit name or ticket/invoice item")
    prompt_hash: str = Field(..., description="SHA-256 hash of the prompt or task specification")
    output_hash: str = Field(..., description="SHA-256 hash of the generated output, diff, file, or report")
    runtime: str = Field(..., description="Runtime/model/tool that produced the output")
    truth_label: Literal["real", "experimental", "partial", "not_configured"] = "experimental"
    customer_hash: Optional[str] = Field(None, description="Optional hash of customer/account ID; never store raw private identity by default")
    contract_ref_hash: Optional[str] = Field(None, description="Optional hash of contract, SOW, invoice, or purchase order")
    amount_usd: Optional[float] = Field(None, ge=0, description="Optional booked or quoted amount linked to this work unit")
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @validator("prompt_hash", "output_hash")
    def hash_like(cls, value: str) -> str:
        value = value.strip().lower()
        if len(value) < 16:
            raise ValueError("hash fields must contain at least 16 hex-like characters")
        return value


class RevenueEventInput(BaseModel):
    event_type: Literal["invoice", "subscription", "license", "usage", "consulting", "grant", "pilot", "other"]
    amount_usd: float = Field(..., ge=0)
    payer_hash: Optional[str] = Field(None, description="Hash of payer/customer identity; do not store raw identity by default")
    receipt_id: Optional[str] = Field(None, description="record_hash of linked work receipt")
    contract_ref_hash: Optional[str] = None
    memo: str = ""
    recurring: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class CollateralReportInput(BaseModel):
    title: str = "OverLLM Financeable Evidence Packet"
    scope: Literal["repository", "customer", "pilot", "grant", "sale", "internal"] = "repository"
    narrative: str = Field(default="", description="Short diligence narrative; avoid inflated valuation claims")
    requested_amount_usd: Optional[float] = Field(None, ge=0)
    metadata: dict[str, Any] = Field(default_factory=dict)


def _safe_sum(values: list[float]) -> float:
    return round(sum(v for v in values if isinstance(v, (int, float))), 2)


def build_finance_summary() -> dict[str, Any]:
    receipts = _read_jsonl(RECEIPTS_PATH)
    revenue = _read_jsonl(REVENUE_PATH)
    reports = _read_jsonl(REPORTS_PATH)

    valid_receipts = [r for r in receipts if r.get("record_type") == "work_receipt"]
    valid_revenue = [r for r in revenue if r.get("record_type") == "revenue_event"]

    receipt_amounts = [float(r.get("payload", {}).get("amount_usd") or 0) for r in valid_receipts]
    revenue_amounts = [float(r.get("payload", {}).get("amount_usd") or 0) for r in valid_revenue]
    recurring_amounts = [
        float(r.get("payload", {}).get("amount_usd") or 0)
        for r in valid_revenue
        if r.get("payload", {}).get("recurring") is True
    ]

    revenue_by_type: dict[str, float] = {}
    for record in valid_revenue:
        payload = record.get("payload", {})
        event_type = str(payload.get("event_type", "other"))
        revenue_by_type[event_type] = round(revenue_by_type.get(event_type, 0.0) + float(payload.get("amount_usd") or 0), 2)

    signed_records = [r for r in receipts + revenue + reports if r.get("signature_status") == "signed"]
    latest_hash = "genesis"
    for path in (REPORTS_PATH, REVENUE_PATH, RECEIPTS_PATH):
        last = _last_hash(path)
        if last != "genesis":
            latest_hash = last
            break

    evidence_score = min(100, len(valid_receipts) * 8 + len(valid_revenue) * 12 + len(signed_records) * 4)
    monetization_score = min(100, int(_safe_sum(revenue_amounts) // 10) + len(valid_revenue) * 10)
    reproducibility_score = min(100, len(valid_receipts) * 10 + (20 if signed_records else 0))

    return {
        "ledger_version": LEDGER_VERSION,
        "generated_at": _utc_now(),
        "truth_label": "financeable_evidence_not_valuation",
        "finance_root": str(FINANCE_ROOT),
        "counts": {
            "work_receipts": len(valid_receipts),
            "revenue_events": len(valid_revenue),
            "collateral_reports": len([r for r in reports if r.get("record_type") == "collateral_report"]),
            "signed_records": len(signed_records),
        },
        "booked_amounts": {
            "receipt_linked_amount_usd": _safe_sum(receipt_amounts),
            "revenue_event_total_usd": _safe_sum(revenue_amounts),
            "recurring_revenue_event_total_usd": _safe_sum(recurring_amounts),
            "revenue_by_type_usd": revenue_by_type,
        },
        "underwriting_kpis": {
            "evidence_score_0_100": evidence_score,
            "monetization_score_0_100": monetization_score,
            "reproducibility_score_0_100": reproducibility_score,
            "financeability_label": "diligence_ready" if evidence_score >= 60 and monetization_score >= 30 else "evidence_building",
            "ledger_head_hash": latest_hash,
        },
        "disclaimer": "These metrics summarize recorded evidence only. They are not a loan approval, securities offering, appraisal, or guaranteed valuation.",
    }


@router.post("/receipts")
async def create_work_receipt(receipt: WorkReceiptInput):
    payload = receipt.dict()
    payload["payload_hash"] = _hash_payload(payload)
    return _append_record(RECEIPTS_PATH, "work_receipt", payload)


@router.get("/receipts")
async def list_work_receipts(limit: int = 100):
    records = _read_jsonl(RECEIPTS_PATH)
    return {"records": records[-limit:], "count": len(records), "truth_label": "ledger_records"}


@router.post("/revenue-events")
async def create_revenue_event(event: RevenueEventInput):
    payload = event.dict()
    if payload.get("receipt_id"):
        receipts = _read_jsonl(RECEIPTS_PATH)
        if not any(r.get("record_hash") == payload["receipt_id"] for r in receipts):
            raise HTTPException(status_code=404, detail="Linked receipt_id not found in local ledger")
    payload["payload_hash"] = _hash_payload(payload)
    return _append_record(REVENUE_PATH, "revenue_event", payload)


@router.get("/revenue-events")
async def list_revenue_events(limit: int = 100):
    records = _read_jsonl(REVENUE_PATH)
    return {"records": records[-limit:], "count": len(records), "truth_label": "ledger_records"}


@router.get("/summary")
async def finance_summary():
    return build_finance_summary()


@router.post("/collateral-report")
async def create_collateral_report(report: CollateralReportInput):
    summary = build_finance_summary()
    payload = report.dict()
    payload["summary"] = summary
    payload["payload_hash"] = _hash_payload(payload)
    return _append_record(REPORTS_PATH, "collateral_report", payload)


@router.get("/collateral-report")
async def latest_collateral_report():
    reports = [r for r in _read_jsonl(REPORTS_PATH) if r.get("record_type") == "collateral_report"]
    if not reports:
        return {
            "status": "not_created",
            "truth_label": "not_configured",
            "summary": build_finance_summary(),
            "message": "POST /api/finance/collateral-report to create a signed/tamper-evident report.",
        }
    return reports[-1]


@router.get("/export.csv")
async def export_finance_csv():
    _ensure_root()
    records = []
    for stream_name, path in (("receipt", RECEIPTS_PATH), ("revenue", REVENUE_PATH), ("report", REPORTS_PATH)):
        for record in _read_jsonl(path):
            payload = record.get("payload", {})
            records.append({
                "stream": stream_name,
                "record_type": record.get("record_type", ""),
                "created_at": record.get("created_at", ""),
                "record_hash": record.get("record_hash", ""),
                "previous_hash": record.get("previous_hash", ""),
                "signature_status": record.get("signature_status", ""),
                "truth_label": payload.get("truth_label", record.get("truth_label", "")),
                "amount_usd": payload.get("amount_usd", ""),
                "event_type": payload.get("event_type", ""),
                "source": payload.get("source", ""),
                "work_unit": payload.get("work_unit", payload.get("memo", payload.get("title", ""))),
                "payload_hash": payload.get("payload_hash", ""),
            })

    temp = tempfile.NamedTemporaryFile("w", delete=False, suffix=".csv", newline="", encoding="utf-8")
    fieldnames = [
        "stream", "record_type", "created_at", "record_hash", "previous_hash", "signature_status",
        "truth_label", "amount_usd", "event_type", "source", "work_unit", "payload_hash",
    ]
    with temp:
        writer = csv.DictWriter(temp, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)
    return FileResponse(temp.name, media_type="text/csv", filename="overllm_financeable_evidence.csv")
