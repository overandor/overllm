# Financeable Features

OverLLM now includes a financeable evidence layer. The goal is not to claim magic collateral or guaranteed valuation. The goal is to make real work auditable enough for buyers, lenders, grant reviewers, fund managers, and enterprise pilots to diligence.

## What changed

### 1. Tamper-evident work receipts

Endpoint:

```http
POST /api/finance/receipts
GET  /api/finance/receipts
```

A receipt records:

- source system
- work unit
- prompt/task hash
- output/diff/report hash
- runtime
- truth label
- optional customer hash
- optional contract/SOW/invoice hash
- optional amount in USD
- payload hash
- ledger hash chain
- optional HMAC-SHA256 signature

Set this for signed records:

```bash
export OVERLLM_LEDGER_SECRET="replace-with-private-diligence-secret"
```

Without a secret, records are still hash-chained but marked `unsigned_local_hash`.

### 2. Revenue events

Endpoint:

```http
POST /api/finance/revenue-events
GET  /api/finance/revenue-events
```

Revenue events support:

- invoice
- subscription
- license
- usage
- consulting
- grant
- pilot
- other

They can link to a work receipt by `receipt_id`, which creates a cleaner diligence path:

```text
customer/payment event -> receipt -> prompt/output hash -> reproducible work artifact
```

### 3. Financeable summary

Endpoint:

```http
GET /api/finance/summary
```

Returns:

- total receipts
- total revenue events
- signed record count
- receipt-linked amount
- revenue event total
- recurring revenue event total
- revenue by type
- evidence score
- monetization score
- reproducibility score
- ledger head hash

These are evidence metrics, not an appraisal.

### 4. Collateral / diligence report

Endpoint:

```http
POST /api/finance/collateral-report
GET  /api/finance/collateral-report
```

Creates a signed or hash-chained report snapshot from the local ledger. This is the file you can attach to:

- buyer diligence
- pilot review
- grant applications
- fund manager update
- bank conversation
- internal CFO packet

### 5. CSV export

Endpoint:

```http
GET /api/finance/export.csv
```

Exports a spreadsheet-friendly evidence ledger with:

- stream
- record type
- created date
- record hash
- previous hash
- signature status
- truth label
- amount
- source/work unit
- payload hash

## CLI usage

Create a receipt from a real file:

```bash
python tools/finance_packet.py receipt \
  --source local.agent \
  --work-unit signed-ledger-api \
  --prompt-text "Add a financeable evidence layer" \
  --output-file api/financeable.py \
  --amount-usd 500 \
  --tag financeable \
  --tag diligence
```

Create a revenue event:

```bash
python tools/finance_packet.py revenue \
  --event-type pilot \
  --amount-usd 500 \
  --memo "Paid pilot for financeable evidence ledger"
```

Create a report:

```bash
python tools/finance_packet.py report \
  --title "OverLLM Financeable Evidence Packet" \
  --scope pilot \
  --narrative "Local-first AI agent with signed work receipts and revenue-linked diligence exports."
```

Print a summary:

```bash
python tools/finance_packet.py summary
```

## Why this is financeable

A repo looks like a toy when it only has demos, claims, and screenshots.

A repo starts becoming financeable when it has:

1. Evidence of work.
2. Evidence of repeatability.
3. Evidence of customer/payment linkage.
4. Evidence of tamper resistance.
5. Evidence of exportability into normal financial review formats.
6. Clear truth labels instead of inflated claims.

This layer moves OverLLM toward that standard.

## What this does not do

It does not create a loan approval.
It does not create a securities offering.
It does not assign a guaranteed valuation.
It does not prove revenue unless the user records real revenue events backed by external evidence.
It does not make mock receipts legitimate.

Use it as an evidence spine, not as a fake appraisal engine.
