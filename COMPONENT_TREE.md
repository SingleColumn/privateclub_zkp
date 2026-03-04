# Component tree — Member screen: "Generate Proof Credential"

Visual design: minimalist, elegant, dark theme. Few primary elements, clear hierarchy, generous spacing.

---

## Tree

```
MemberGenerateScreen
├── Header
│   ├── title: "Generate Proof Credential"
│   ├── subtitle: "Share a private proof of your funds."
│   └── optional: "How this works" link
│
├── TierSelector
│   └── TierCard (×4)
│       ├── label (e.g. "≥ €250k")
│       ├── optional helper text
│       └── selected state (border + check)
│
├── StatusRow
│   ├── IntegrityPill
│   │   └── status: OK | Checking… | Failed
│   └── TimestampLabel
│       └── "Will be set when you generate" | "2 min ago" / ISO
│
├── PrimaryActionButton
│   └── "Generate credential" | "Generating…" (loading)
│
├── PrivacyNote (fine print under button)
│   ├── "Reveals only the selected tier, not your exact balance."
│   └── "This is not a reservation or lock of funds."
│
├── ErrorBanner | DegradedBanner (conditional)
│   └── message + optional dismiss
│
└── CredentialPanel (visible after success)
    ├── CredentialSummary
    │   ├── Tier proven: "≥ €250k"
    │   └── Issued at: "2 min ago"
    ├── QrCard
    │   └── QR code image/placeholder
    ├── TokenField
    │   ├── truncated token text
    │   └── Copy button
    ├── ShareLinkButton — "Copy share link"
    └── RegenerateButton — "Regenerate" (secondary)
```

---

## Component responsibilities

| Component | Props / state | Notes |
|-----------|----------------|--------|
| **MemberGenerateScreen** | `tiers`, local state: selectedTier, status (idle \| generating \| generated \| error), integrity, issuedAt, token, errorMessage | Page container; owns flow state. |
| **Header** | `title`, `subtitle`, `helpLink?` | Static copy. |
| **TierSelector** | `tiers`, `selectedId`, `onSelect` | Renders list of TierCard. |
| **TierCard** | `tier`, `selected`, `onSelect` | Single tier option; selected styling. |
| **StatusRow** | `integrityStatus`, `timestampLabel` | Two-column layout. |
| **IntegrityPill** | `status: 'OK' \| 'CHECKING' \| 'FAIL'` | Pill with color variant. |
| **TimestampLabel** | `label`, `value` | Label + value text. |
| **PrimaryActionButton** | `loading`, `onClick`, `children` | Primary CTA; disabled when loading. |
| **PrivacyNote** | — | Static two-line copy. |
| **ErrorBanner** | `message`, `variant: 'error' \| 'degraded'` | Inline banner. |
| **CredentialPanel** | `tierLabel`, `issuedAtLabel`, `token`, `shareLink`, `onRegenerate` | Shown when status === 'generated'. |
| **CredentialSummary** | `tierLabel`, `issuedAtLabel` | Two-field summary row. |
| **QrCard** | `value` (token or link for QR) | Dark card with QR placeholder/svg. |
| **TokenField** | `token`, `onCopy` | Read-only field + Copy. |
| **ShareLinkButton** | `onCopyLink` | Button to copy link. |
| **RegenerateButton** | `onClick` | Text/secondary button. |

---

## UX states (from PRD §8)

- **Idle** — choose tier; integrity and timestamp shown; Generate enabled.
- **Generating…** — button loading; optional disabled tier selection.
- **Generated** — CredentialPanel visible; QR + token + share link + Regenerate.
- **Error** — ErrorBanner with reason (integrity fail, insufficient funds, unexpected).
