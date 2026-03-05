# PRD (Draft) — Proof of Funds Credential for private club (Mock UIs + Python Flow Simulation)

**Version:** 0.2  
**Date:** 2026-02-25  
**Purpose of this PRD:** Define enough product behavior to (1) generate **mock UIs** for the Member “Generate Credential” screen and the Verifier “Receive/Verify Credential” screen, and (2) build a **Python simulation** of the flow using mock data, with ZKP implemented as **stub functions** that run “separately” for Member and Verifier.

---

## 1) Context and problem

The club is invitation-only. Members share business and investment opportunities. Trust and deal velocity suffer because some members pretend to have money to invest (funds) but do not. The goal is to **filter posers and reduce nosy behavior** with a lightweight proof mechanism.

A key privacy requirement: members must be able to **proactively generate a credential** and **choose who to share it with**, avoiding interactive or reactive “prove funds ≥ X” requests from other club members that could allow coordinated groups to infer balance ranges.

---

## 2) Goals and non-goals

### Goals
1. **Member-controlled sharing:** Member generates a proof credential and shares it selectively (not public).
2. **Low friction:** Creating and verifying a credential takes seconds.
3. **Privacy-preserving:** Credential reveals only a **coarse tier claim** (e.g., “≥ €250k”) and a timestamp—no exact balances, no account identifiers.
4. **Mockable:** The behavior is specified clearly enough for UI mocks and a Python simulation.

### Non-goals for this stage
- Integrations with real PSD2 providers/banks.
- Club-issued credentials or server-side issuance.
- Verifier-side validation of PSD2 session data with providers.
- Guaranteeing funds remain available after proof (no escrow/lock).

---

## 3) Core concept

A **Proof Credential** is a shareable artifact created by the member that states:

> “As of timestamp T, this member meets Tier N (≥ threshold).”

The credential is designed to be:
- **Member-chosen tier only** (no arbitrary verifier-requested thresholds).
- **Selective share:** member chooses recipients (e.g., share link/token in chat).
- **Timestamped:** verifier can decide whether the credential is “recent enough” for their context.

**Note on recency:** Credentials do **not** need to expire in this stage. The credential includes an `issued_at` timestamp, and the verifier decides if the credential is recent enough.

---

## 4) Scope for mock UIs

Only two screens must be mock-designed now.

## Visual design guidelines (for mocks)

- **Overall style**: minimalist, elegant, low-noise UI.
- **Theme**: dark background with high-contrast, non-neon accent colors.
- **Typography**: clean sans-serif; avoid playful fonts.
- **Tone**: professional and club-like, not a busy “fintech dashboard”.
- **Layout**: few primary elements per screen, clear hierarchy, generous spacing.

### A) Member screen: “Generate Proof Credential”
Purpose: member chooses a tier and generates a shareable credential.

**UI requirements**
- Tier selection (coarse tiers only, configurable):
  - Example: ≥ €250k, ≥ €500k, ≥ €1m, ≥ €2.5m
- Recency display (e.g., “Timestamp: now” after generation)
- Integrity status indicator (e.g., “Device integrity: OK”)
- Primary action: **Generate credential**
- Output: a shareable **credential token** (QR + share link/button)
- Secondary: “Regenerate” (optional)

**Copy requirements**
- Privacy note: “Reveals only the selected tier, not your balance.”
- Limitation note: “This is not a reservation of funds.”

### B) Verifier screen: “Verify Received Credential”
Purpose: verifier receives a credential token and verifies it.

**UI requirements**
- Input methods:
  - “Open credential link” (deep link) OR “Paste token” OR “Scan QR”
- Result states:
  - PASS (Tier shown + timestamp + integrity)
  - FAIL (reason)
- Display fields:
  - Tier proven (e.g., “≥ €250k”)
  - Issued at / age (e.g., “Issued 2h ago”)
  - Integrity status (OK / FAIL / UNSUPPORTED)
- “Recency guidance” UI element (e.g., text: “Decide if this is recent enough for your needs.”)

**Preferred verifier flow (link-first UX)**  
When a verifier receives a credential link (e.g. from a messaging app), **clicking the link** should open the verifier experience (app or web) with the credential **already loaded** from the URL. The verifier then sees the credential and can run verification with one action (e.g. “Verify”); no copy-paste of the link or token should be required. Paste and QR remain as fallbacks when the verifier does not have the link in clickable form.

---

## 5) Credential sharing model

Credentials are **not public**. A member shares a credential intentionally with chosen recipients.

**Share channels**
- Message link (preferred)
- Token string copy/paste (fallback)
- QR code (in-person)

**Privacy properties**
- Verifier cannot request arbitrary thresholds.
- Sharing the same credential with multiple people reveals the same tier—no incremental leakage.
- Member may generate different credentials at different tiers, but this is an explicit choice.

**Screenshot and forwarding behavior**
- Screenshots and forwarding of a received credential are **discouraged**.
- If a **receiving member** takes a screenshot of the credential view or uses a system/UI share action to forward the credential, the app **must display a notification** warning that this behavior may not respect the club’s commitment to confidentiality.
- When such a screenshot or forwarding action is detected, the **member who originally shared the credential must also be notified** (e.g. in-app notification or activity entry such as “Your credential shared with @member-xyz was captured/forwarded on [timestamp]”).

**Operational rule**
- Credential tokens should be **opaque** (no readable tier/balance in the token itself). Tier is revealed only after verification/parsing inside the verifier app/script.

---

## 6) Data objects (for simulation + UI binding)

### 6.1 Tier configuration
```json
{
  "tiers": [
    {"id": "TIER_250K", "threshold": 250000,   "currency": "EUR", "label": "≥ €250k"},
    {"id": "TIER_500K", "threshold": 500000,   "currency": "EUR", "label": "≥ €500k"},
    {"id": "TIER_1M",   "threshold": 1000000,  "currency": "EUR", "label": "≥ €1m"},
    {"id": "TIER_2_5M", "threshold": 2500000, "currency": "EUR", "label": "≥ €2.5m"}
  ]
}
```

### 6.2 Mock “account snapshot” (member-side only)
```json
{
  "account_holder": "Member Name",
  "balance": 350000,
  "currency": "EUR",
  "fetched_at": "ISO-8601"
}
```

### 6.3 Integrity attestation (mock)
```json
{
  "status": "OK|FAIL|UNSUPPORTED",
  "platform": "iOS|Android",
  "risk_flags": ["ROOTED", "DEBUGGER_DETECTED"],
  "attested_at": "ISO-8601"
}
```

### 6.4 Credential payload (what the proof attests to)
```json
{
  "credential_id": "uuid",
  "member_pseudonym": "member-xyz",
  "tier_id": "TIER_250K",
  "issued_at": "ISO-8601",
  "integrity": { "...": "..." }
}
```

### 6.5 Proof package (shared token decodes to this)
```json
{
  "credential_payload": { "...": "..." },
  "zkp_proof": "opaque-string-or-bytes",
  "token_version": "v1"
}
```

---

## 7) Python simulation requirements

### 7.1 Simulation structure
The simulation should mimic two separate devices:
- `member_device.py` (member generates credential + proof)
- `verifier_device.py` (verifier verifies proof + displays result)

A third file may orchestrate an end-to-end demo:
- `demo_flow.py` (creates mock member balance, triggers member credential generation, passes token to verifier)

### 7.2 ZKP implementation

See the document zkp_architecture.md.

### 7.3 Tokenization helpers
- `encode_token(proof_package) -> str` (e.g., base64url JSON)
- `decode_token(token) -> proof_package`

### 7.4 Verification checks (non-crypto)
Verifier must check:
1. Credential token is well-formed and decodes correctly.
2. `integrity.status == OK` (or display degraded state if policy allows).
3. `zkp_verify(...) == True`.
4. Display `issued_at` and let the verifier decide if it’s recent enough.

### 7.5 Test scenarios (must be supported)
1. PASS: balance 350k, tier 250k
2. FAIL: balance 350k, tier 1m
3. Degraded/FAIL: integrity FAIL/UNSUPPORTED
4. Corrupted token / malformed proof
5. Old timestamp: show PASS but clearly display “issued X days ago”

---

## 8) UX states and copy (for mocks)

### Member “Generate” states
- Idle (choose tier)
- Generating…
- Generated (share options)
- Error (integrity fail, insufficient funds for chosen tier, unexpected error)

### Verifier “Verify” states
- Waiting for credential
- Verifying…
- PASS
- FAIL (show reason)
- Degraded (if integrity is unsupported but policy allows display)

---

## 9) Main security risks (explicitly acknowledged)

1. **Device compromise / app tampering:** A skilled attacker may fake local balance inputs or bypass integrity checks. (Integrity attestation reduces risk but is not a guarantee.)
2. **No external truth validation:** Without verifier-side PSD2 session validation or an issuer signature, the verifier ultimately trusts that the member device used genuine data.
3. **Credential forwarding:** A recipient can forward the credential to others. Current mitigation: in-app warnings to the recipient and notifications to the original sharer when screenshot/forward events are detected. Additional options (future): recipient-bound credentials, short-lived one-time tokens, watermarking.
4. **Tier leakage by design:** Coarse tiers still reveal some information (e.g., “≥ €250k”). This is a conscious tradeoff for utility.
5. **Borrowed/temporary funds:** A member can temporarily inflate balances to generate a credential, then move funds away.
