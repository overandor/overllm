# Mac-Native iMessage + Ollama + Memory Intelligence OS

This is the strongest commercial wedge for OverLLM: a Mac-native messaging copilot that uses iMessage as the user-owned communication surface, Ollama as the local reasoning engine, and a memory ledger as the intelligence layer.

This is not a spam bot. It is a consent-aware local operator for the user's own conversations, leads, follow-ups, service workflows, and revenue evidence.

## Product definition

OverLLM Messages OS is a local-first Mac application that turns the user's Apple Messages workflow into an auditable customer-intelligence system.

The core loop:

```text
conversation context -> local memory -> Ollama reasoning -> approved message -> iMessage send -> reply capture -> receipt -> revenue attribution
```

## Why this is more financeable than a generic AI agent

A generic AI agent is hard to price because it looks like a demo.

A Mac-native iMessage memory system is financeable because it attaches to measurable business activity:

- outbound lead conversations
- inbound replies
- booked appointments
- repeat customer memory
- quote/invoice follow-up
- revenue attribution
- signed proof of performed outreach
- exportable diligence records

The buyer can understand the value immediately: more replies, faster follow-up, better customer memory, less manual texting, clearer conversion evidence.

## Native Mac surfaces

The product should be packaged as a Mac app with these surfaces:

| Surface | Purpose |
|---|---|
| Menu bar app | Start/stop local assistant, see queue, memory, safety state |
| Message composer | Drafts replies and outreach with local Ollama |
| Approval gate | User must approve sends unless a contact is explicitly allowlisted |
| Contact memory | Remembers preferences, prior offers, bookings, objections, STOP status |
| Follow-up queue | Shows who needs a reply, who is warm, who is stale |
| Revenue ledger | Links conversations to paid events, pilots, appointments, invoices |
| Receipt viewer | Shows hash-linked proof of sent/approved work units |
| Export panel | CSV/PDF evidence packet for buyer, lender, grant, or partner review |

## Local Ollama intelligence

Ollama should run locally and serve as the private reasoning layer.

The Mac app should use Ollama for:

- contact-specific reply drafting
- tone matching
- lead scoring
- next-best-action suggestions
- conversation summarization
- objection detection
- appointment intent detection
- safety and compliance checks
- memory extraction
- campaign variant scoring

The product should not require cloud LLM calls for normal operation. Cloud providers can be optional, but the default value proposition is local intelligence.

## Memory intelligence

Memory is the moat.

The app should maintain a local memory store with:

- contact hash
- display name or local alias
- phone/address only when user permits storage
- consent status
- STOP/DNC status
- last message timestamp
- last reply timestamp
- preferred tone
- buyer/service intent
- objections
- booking status
- revenue status
- notes
- summary embeddings
- message receipt hashes

Memory should be local-first, exportable, and deletable.

## Safe iMessage boundary

This must remain consent-safe and user-controlled.

Required boundaries:

- No unsolicited bulk spam mode.
- No hidden sending.
- No bypassing Apple security prompts.
- No scraping unrelated private data.
- No sending to contacts marked STOP or DNC.
- No sending without an approval gate unless the user explicitly allowlists that contact/workflow.
- Rate limits and quiet hours must be enforced.
- Every outbound message should produce a receipt.

The financeable version is not “send a million texts.” The financeable version is “local relationship intelligence with proof, memory, and revenue attribution.”

## Message workflow states

Each contact should move through clear states:

| State | Meaning |
|---|---|
| cold | contact exists but no active permission or prior context |
| warm | contact replied or showed intent |
| active | conversation is ongoing |
| awaiting_user | user needs to approve or answer |
| follow_up_due | safe follow-up window is open |
| booked | appointment/pilot/meeting booked |
| paid | revenue event recorded |
| stopped | do not contact |
| archived | inactive or intentionally closed |

## Financeable events

The iMessage system should emit financeable events into the existing finance ledger:

| Event | Ledger destination |
|---|---|
| approved outbound message | work receipt |
| meaningful reply | work receipt |
| appointment booked | revenue or pipeline event |
| invoice sent | revenue event |
| payment received | revenue event |
| campaign exported | collateral report |
| conversation summary generated | work receipt |

This creates the diligence chain:

```text
message -> reply -> booking -> payment -> receipt -> CSV export -> collateral report
```

## Differentiation

This is not just a CRM.

It is:

- local-first
- Mac-native
- iMessage-native
- Ollama-powered
- memory-aware
- consent-aware
- receipt-producing
- revenue-attributing
- exportable for diligence

That combination is the product.

## MVP requirements

A serious MVP needs:

1. Menu bar app.
2. Local Ollama connection status.
3. Contact memory database.
4. Draft-only composer.
5. Manual approval before send.
6. STOP/DNC ledger.
7. Quiet hours.
8. Follow-up queue.
9. Reply summarizer.
10. Receipt emission.
11. Revenue event linkage.
12. CSV export.

## Demo script

A financeable demo should show:

1. User receives or selects a conversation.
2. App summarizes contact history locally.
3. Ollama drafts a reply.
4. User approves the send.
5. App records a signed work receipt.
6. Contact replies.
7. App scores intent and suggests follow-up.
8. Booking or pilot is recorded.
9. Revenue event is linked.
10. Collateral report and CSV export are generated.

That is a buyer-understandable flow.

## Truth labels

| Claim | Truth label |
|---|---|
| Native Mac app | planned / partial until Swift target exists |
| Local Ollama reasoning | real if Ollama is reachable |
| iMessage send | Mac-local user-controlled automation only |
| Bulk outreach | disabled / not a product goal |
| Memory intelligence | planned / partial until DB and embeddings are wired |
| Financeable evidence | real local ledger |
| Revenue attribution | real only when user records real payments/events |

## Positioning

Best positioning:

> A local Mac messaging copilot that turns iMessage conversations into memory, follow-up intelligence, signed work receipts, and revenue-linked diligence exports.

Bad positioning:

> AI spam sender.

Do not sell it as a spam sender. Sell it as local customer intelligence and proof-of-work messaging for solo operators, service businesses, recruiters, sales teams, creators, and field operators.
