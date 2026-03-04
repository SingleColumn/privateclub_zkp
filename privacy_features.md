# Privacy Features Overview --- Proof of Funds Credential App

**Author:** Lead Developer\
**Date:** 2026-02-26

------------------------------------------------------------------------

## 1. Purpose

This document outlines the primary privacy protections built into the
Proof of Funds Credential App.\
The system is designed to allow members to demonstrate financial
capability while minimizing disclosure of sensitive financial
information.

Privacy is treated as a first-class design principle.

------------------------------------------------------------------------

## 2. Data Minimization by Design

The app follows strict data minimization principles:

-   No exact account balances are shared with verifiers.
-   No account numbers are stored or transmitted.
-   No bank or custodian names are revealed to verifiers.
-   No transaction history is collected or exposed.
-   No financial data is transmitted to club servers.

Only the following information is included in a credential:

-   Selected tier (e.g., ≥ €250k)
-   Timestamp of credential generation
-   Device integrity status
-   Pseudonymous member identifier

------------------------------------------------------------------------

## 3. Tier-Based Disclosure (Coarse Granularity)

The system uses predefined financial tiers rather than arbitrary
thresholds.

This ensures:

-   Verifiers cannot "probe" for precise balances.
-   Members choose what level of financial capability to disclose.
-   Repeated verifications do not incrementally reveal additional
    financial information.

Example tiers:

-   ≥ €50k\
-   ≥ €250k\
-   ≥ €1m\
-   ≥ €5m

Only the selected tier is revealed --- not the underlying balance.

------------------------------------------------------------------------

## 4. Member-Controlled Sharing

Credentials are:

-   Generated proactively by the member.
-   Shared only with chosen recipients.
-   Not publicly visible or broadcast.

Members control:

-   When a credential is generated.
-   Which tier is disclosed.
-   Who receives the credential token.

There is no central directory of member financial tiers.

------------------------------------------------------------------------

## 5. No Central Financial Database

The club does not operate a financial database.

The system does not:

-   Store member balances.
-   Maintain historical financial records.
-   Aggregate financial data across members.

Financial data processing (in the current design stage) occurs only
locally on the member's device.

------------------------------------------------------------------------

## 6. Pseudonymous Identifiers

Credentials use pseudonymous member identifiers rather than legal names.

This reduces:

-   Cross-platform correlation risk.
-   Accidental identity leakage.
-   Exposure of sensitive personal information.

------------------------------------------------------------------------

## 7. No Continuous Monitoring

The app does not:

-   Continuously monitor accounts.
-   Automatically refresh balances in the background.
-   Track ongoing financial changes.

A credential reflects only the state at the moment of generation.

------------------------------------------------------------------------

## 8. Local-Only Financial Processing

In the current architecture:

-   Financial snapshot data is processed locally on the member's device.
-   Only the derived tier result is used in the credential.
-   Raw balance values are not embedded in shared tokens.

------------------------------------------------------------------------

## 9. Opaque Credential Tokens

Shared credential tokens:

-   Do not contain readable financial values.
-   Are encoded in opaque form (e.g., base64url JSON).
-   Require decoding and verification within the verifier app.

This prevents casual inspection of credential contents in messaging
apps.

------------------------------------------------------------------------

## 10. Open Source Transparency

If the app is open source:

-   Members can verify that no hidden data collection exists.
-   Members can confirm that balances are not transmitted externally.
-   Members can inspect how tier selection is implemented.

Privacy protections do not rely on secrecy.

------------------------------------------------------------------------

## 11. Human-Controlled Recency Policy

Credentials include a timestamp.

Rather than automatic expiration:

-   Verifiers decide whether a credential is recent enough.
-   Different social contexts may apply different recency expectations.

This avoids unnecessary background data refreshes while maintaining
flexibility.

------------------------------------------------------------------------

## 12. Known Privacy Tradeoffs

The system intentionally reveals:

-   That a member meets a selected financial tier.
-   The timestamp of generation.

It does not attempt to hide:

-   That the member chose to share a credential.
-   The general magnitude category (tier) of funds.

This tradeoff balances utility and discretion.

------------------------------------------------------------------------

## 13. Summary

The app's privacy model is built on:

1.  Minimal disclosure (tier, not balance)\
2.  Member-controlled sharing\
3.  No central financial storage\
4.  Local-only processing of sensitive data\
5.  Transparent, inspectable codebase

The system enables social trust signaling while minimizing exposure of
sensitive financial information.
