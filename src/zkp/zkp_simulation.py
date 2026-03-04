"""
zkp_simulation.py - Python simulation of the Proof-of-Funds credential flow (PRD 7).

Mimics two logical devices:
- Member: generates credential + ZKP, produces shareable token.
- Verifier: decodes token, checks integrity and ZKP, displays result.

Uses engine.py for zkp_setup, zkp_prove, zkp_verify. Run as:
  python -m src.zkp.zkp_simulation

This script also writes a JSON audit report into a local reports/ folder
named audit_report_[timestamp].json, so an independent user can inspect
inputs, tokens, and verification results.

Note: If scenario 1 (PASS) shows "proof verification failed", the engine's
verify path may have a bug; the simulation logic is correct.
"""

from __future__ import annotations

import base64
import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    from .engine import zkp_setup, zkp_prove, zkp_verify
except ImportError:
    from engine import zkp_setup, zkp_prove, zkp_verify


# ------------------------- Tier configuration (PRD §6.1) -------------------------

TIER_CONFIG: Dict[str, Any] = {
    "tiers": [
        {"id": "TIER_250K", "threshold": 250000, "currency": "EUR", "label": "≥ €250k"},
        {"id": "TIER_500K", "threshold": 500000, "currency": "EUR", "label": "≥ €500k"},
        {"id": "TIER_1M", "threshold": 1000000, "currency": "EUR", "label": "≥ €1m"},
        {"id": "TIER_2_5M", "threshold": 2500000, "currency": "EUR", "label": "≥ €2.5m"},
    ]
}

def get_threshold_for_tier(tier_id: str) -> Optional[int]:
    for t in TIER_CONFIG["tiers"]:
        if t["id"] == tier_id:
            return t["threshold"]
    return None

def get_tier_label(tier_id: str) -> str:
    for t in TIER_CONFIG["tiers"]:
        if t["id"] == tier_id:
            return t["label"]
    return tier_id

def _safe_label(label: Optional[str]) -> str:
    """ASCII-safe tier label for console output (e.g. Windows cp1252)."""
    if not label:
        return ""
    return label.replace("\u2265", ">=")


# ------------------------- Audit logging -------------------------

AUDIT_EVENTS: List[Dict[str, Any]] = []


def _audit_add(entry: Dict[str, Any]) -> None:
    AUDIT_EVENTS.append(entry)


def _write_audit_report(params: Dict[str, Any]) -> Path:
    """
    Write accumulated audit events to reports/audit_report_[timestamp].json.
    """
    now = datetime.now(timezone.utc)
    ts = now.strftime("%Y%m%dT%H%M%SZ")
    reports_dir = Path.cwd() / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    report_path = reports_dir / f"audit_report_{ts}.json"

    domain_sep = params.get("domain_separator")
    if isinstance(domain_sep, (bytes, bytearray)):
        domain_sep = domain_sep.decode("utf-8", errors="ignore")

    report = {
        "generated_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "engine": {
            "curve": params.get("curve"),
            "n_bits": params.get("n_bits"),
            "domain_separator": domain_sep,
        },
        "tier_config": TIER_CONFIG,
        "events": AUDIT_EVENTS,
    }

    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report_path


# ------------------------- Tokenization (PRD §7.3) -------------------------

def encode_token(proof_package: Dict[str, Any]) -> str:
    """Encode proof package to opaque base64url JSON string."""
    raw = json.dumps(proof_package, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")

def decode_token(token: str) -> Tuple[Dict[str, Any], Optional[str]]:
    """
    Decode token to proof package. Returns (proof_package, None) on success,
    or ({}, "error reason") on failure.
    """
    try:
        pad = 4 - (len(token) % 4)
        if pad != 4:
            token += "=" * pad
        raw = base64.urlsafe_b64decode(token.encode("ascii"))
        data = json.loads(raw.decode("utf-8"))
        if not isinstance(data, dict):
            return {}, "invalid token structure"
        if "credential_payload" not in data or "zkp_proof" not in data:
            return {}, "missing credential_payload or zkp_proof"
        return data, None
    except (ValueError, json.JSONDecodeError, KeyError) as e:
        return {}, f"malformed token: {e}"


# ------------------------- Data builders (PRD §6.2–6.4) -------------------------

def make_integrity(status: str = "OK", platform: str = "iOS", risk_flags: Optional[List[str]] = None) -> Dict[str, Any]:
    return {
        "status": status,
        "platform": platform,
        "risk_flags": risk_flags or [],
        "attested_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }

def make_credential_payload(
    tier_id: str,
    member_pseudonym: str = "member-xyz",
    issued_at: Optional[datetime] = None,
    integrity: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    now = issued_at or datetime.now(timezone.utc)
    return {
        "credential_id": str(uuid.uuid4()),
        "member_pseudonym": member_pseudonym,
        "tier_id": tier_id,
        "issued_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "integrity": integrity if integrity is not None else make_integrity(),
    }


# ------------------------- Verifier result -------------------------

@dataclass
class VerifierResult:
    status: str  # "PASS" | "FAIL" | "DEGRADED"
    reason: str
    tier_id: Optional[str] = None
    tier_label: Optional[str] = None
    issued_at: Optional[str] = None
    age_human: Optional[str] = None
    integrity_status: Optional[str] = None


def _age_human(issued_at_iso: str) -> str:
    try:
        dt = datetime.fromisoformat(issued_at_iso.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        delta = now - dt
        days = delta.days
        if days > 0:
            return f"{days} day{'s' if days != 1 else ''} ago"
        secs = int(delta.total_seconds())
        if secs >= 3600:
            return f"{secs // 3600}h ago"
        if secs >= 60:
            return f"{secs // 60}m ago"
        return "just now"
    except Exception:
        return "unknown"


# ------------------------- Member flow -------------------------

def member_generate_token(
    params: Dict[str, Any],
    balance: int,
    tier_id: str,
    member_pseudonym: str = "member-xyz",
    integrity_status: str = "OK",
    issued_at: Optional[datetime] = None,
) -> Tuple[Optional[str], Optional[str]]:
    """
    Member-side function: builds credential, runs ZKP, returns shareable token.
    Returns (token, None) on success, or (None, "error reason") on failure.
    The returned token is the shareable proof-of-funds credential; 
    it is intended to be sent to the verifier for verification.
    'token' is a base64-encoded JSON string containing:
      - 'credential_payload': dict created by make_credential_payload(), with fields like tier_id, member_pseudonym, issued_at, integrity, etc.
      - 'zkp_proof': dict created by zkp_prove(), containing the zero-knowledge proof data
      - 'token_version': version string (e.g., "v1")
    # If the function returns None for the token (i.e., (None, error)), it indicates a failure case;
    # 'token' will be None and a corresponding error string will be provided (e.g., due to unknown tier
    # or insufficient funds). A return value of None for token always means there was an error.
    """
    threshold = get_threshold_for_tier(tier_id)
    if threshold is None:
        return None, f"unknown tier: {tier_id}"
    if balance < threshold:
        return None, "insufficient funds for chosen tier (balance < threshold)"

    # 'integrity' contains metadata about the credential's integrity status (e.g., "OK" or other status),
    # indicating whether the credential payload is complete, verified, or potentially degraded.
    integrity = make_integrity(status=integrity_status)
    
    credential_payload = make_credential_payload(
        tier_id=tier_id,
        member_pseudonym=member_pseudonym,
        issued_at=issued_at,
        integrity=integrity,
    )

    try:
        zkp_proof = zkp_prove(params, balance=balance, threshold=threshold, credential_payload=credential_payload)
    except ValueError as e:
        return None, str(e)

    proof_package = {
        "credential_payload": credential_payload,
        "zkp_proof": zkp_proof,
        "token_version": "v1",
    }
    return encode_token(proof_package), None


# ------------------------- Verifier flow (PRD §7.4) -------------------------

def verifier_verify(
    params: Dict[str, Any],
    token: str,
    allow_degraded_integrity: bool = False,
) -> VerifierResult:
    """
    Verifier-side: decode token, check integrity, run zkp_verify, return result.
    """
    proof_package, decode_error = decode_token(token)
    if decode_error:
        return VerifierResult(status="FAIL", reason=decode_error)

    cred = proof_package.get("credential_payload") or {}
    zkp = proof_package.get("zkp_proof")
    tier_id = cred.get("tier_id")
    issued_at = cred.get("issued_at")
    integrity = cred.get("integrity") or {}
    integrity_status = integrity.get("status", "UNSUPPORTED")

    if not zkp or not isinstance(zkp, dict):
        return VerifierResult(status="FAIL", reason="missing or invalid zkp_proof")

    threshold = get_threshold_for_tier(tier_id) if tier_id else None
    if threshold is None:
        return VerifierResult(
            status="FAIL",
            reason=f"unknown tier_id in credential: {tier_id}",
            tier_id=tier_id,
            issued_at=issued_at,
            age_human=_age_human(issued_at) if issued_at else None,
            integrity_status=integrity_status,
        )

    if integrity_status != "OK":
        if allow_degraded_integrity:
            # Still run ZKP; may return DEGRADED if ZKP passes
            pass
        else:
            return VerifierResult(
                status="FAIL",
                reason=f"integrity status not OK: {integrity_status}",
                tier_id=tier_id,
                tier_label=get_tier_label(tier_id),
                issued_at=issued_at,
                age_human=_age_human(issued_at) if issued_at else None,
                integrity_status=integrity_status,
            )

    zkp_valid = zkp_verify(params, threshold=threshold, credential_payload=cred, proof_package=zkp)
    if not zkp_valid:
        return VerifierResult(
            status="FAIL",
            reason="proof verification failed",
            tier_id=tier_id,
            tier_label=get_tier_label(tier_id),
            issued_at=issued_at,
            age_human=_age_human(issued_at) if issued_at else None,
            integrity_status=integrity_status,
        )

    if integrity_status != "OK" and allow_degraded_integrity:
        return VerifierResult(
            status="DEGRADED",
            reason="proof valid but integrity not OK",
            tier_id=tier_id,
            tier_label=get_tier_label(tier_id),
            issued_at=issued_at,
            age_human=_age_human(issued_at) if issued_at else None,
            integrity_status=integrity_status,
        )

    return VerifierResult(
        status="PASS",
        reason="credential valid",
        tier_id=tier_id,
        tier_label=get_tier_label(tier_id),
        issued_at=issued_at,
        age_human=_age_human(issued_at) if issued_at else None,
        integrity_status=integrity_status,
    )


# ------------------------- Test scenarios (PRD §7.5) -------------------------

SCENARIO_MENU = """
=== ZKP simulation - PRD 7.5 test scenarios ===

Select a scenario to run:
  1. PASS: balance 350k, tier 250k
  2. FAIL: balance 350k, tier 1m (insufficient funds)
  3. FAIL: integrity status FAIL (strict vs allow degraded)
  4. FAIL: corrupted / malformed token
  5. PASS: old timestamp (issued 10 days ago)
  6. Demo flow: single member generate -> verifier verify
"""


def _run_helper(token: Optional[str], allow_degraded: bool, params: Dict[str, Any]) -> VerifierResult:
    if token is None:
        return VerifierResult(status="FAIL", reason="(no token: member generation failed)")
    return verifier_verify(params, token, allow_degraded_integrity=allow_degraded)


def run_single_scenario(params: Dict[str, Any], scenario_id: int) -> None:
    """Run one PRD §7.5 test scenario by number (1-5) and print + audit result."""
    from datetime import timedelta

    if scenario_id == 1:
        print("1. PASS: balance 350k, tier 250k")
        token1, err1 = member_generate_token(params, balance=350000, tier_id="TIER_250K")
        res1 = _run_helper(token1, False, params)
        print(f"   Member: {'token generated' if token1 else err1}")
        print(f"   Verifier: {res1.status} - {res1.reason}")
        if res1.tier_label:
            print(f"   Tier: {_safe_label(res1.tier_label)}, issued {res1.age_human or '?'}")
        _audit_add(
            {
                "kind": "scenario",
                "id": "1",
                "description": "PASS: balance 350k, tier 250k",
                "member": {
                    "inputs": {"balance": 350000, "tier_id": "TIER_250K"},
                    "outputs": {"token": token1, "error": err1},
                    "decoded_proof_package": decode_token(token1)[0] if token1 else None,
                },
                "verifier": {
                    "inputs": {"allow_degraded_integrity": False},
                    "outputs": res1.__dict__,
                },
            }
        )
    elif scenario_id == 2:
        print("2. FAIL: balance 350k, tier 1m (insufficient funds)")
        token2, err2 = member_generate_token(params, balance=350000, tier_id="TIER_1M")
        res2 = _run_helper(token2, False, params)
        print(f"   Member: {'token generated' if token2 else err2}")
        if not token2:
            print("   Verifier: (no token to verify)")
        else:
            print(f"   Verifier: {res2.status} - {res2.reason}")
        _audit_add(
            {
                "kind": "scenario",
                "id": "2",
                "description": "FAIL: balance 350k, tier 1m (insufficient funds)",
                "member": {
                    "inputs": {"balance": 350000, "tier_id": "TIER_1M"},
                    "outputs": {"token": token2, "error": err2},
                },
                "verifier": {
                    "inputs": {"allow_degraded_integrity": False},
                    "outputs": res2.__dict__ if token2 else {"status": "SKIPPED", "reason": "no token"},
                },
            }
        )
    elif scenario_id == 3:
        print("3. FAIL: integrity status FAIL")
        token3, err3 = member_generate_token(params, balance=500000, tier_id="TIER_250K", integrity_status="FAIL")
        res3 = _run_helper(token3, False, params)
        print(f"   Verifier (strict): {res3.status} - {res3.reason}")
        res3b = verifier_verify(params, token3 or "", allow_degraded_integrity=True)
        print(f"   Verifier (allow degraded): {res3b.status} - {res3b.reason}")
        _audit_add(
            {
                "kind": "scenario",
                "id": "3",
                "description": "Integrity FAIL / degraded",
                "member": {
                    "inputs": {"balance": 500000, "tier_id": "TIER_250K", "integrity_status": "FAIL"},
                    "outputs": {"token": token3, "error": err3},
                    "decoded_proof_package": decode_token(token3)[0] if token3 else None,
                },
                "verifier": {
                    "strict": {"inputs": {"allow_degraded_integrity": False}, "outputs": res3.__dict__},
                    "allow_degraded": {
                        "inputs": {"allow_degraded_integrity": True},
                        "outputs": res3b.__dict__,
                    },
                },
            }
        )
    elif scenario_id == 4:
        print("4. FAIL: corrupted token")
        bad_token = "not-valid-base64!!!"
        res4 = verifier_verify(params, bad_token)
        print(f"   Verifier: {res4.status} - {res4.reason}")
        missing_zkp_token = encode_token({"credential_payload": {}, "token_version": "v1"})
        res4b = verifier_verify(params, missing_zkp_token)
        print(f"   Verifier (missing zkp_proof): {res4b.status} - {res4b.reason}")
        _audit_add(
            {
                "kind": "scenario",
                "id": "4",
                "description": "Corrupted / malformed tokens",
                "cases": [
                    {
                        "label": "invalid base64",
                        "inputs": {"token": bad_token, "allow_degraded_integrity": False},
                        "outputs": res4.__dict__,
                    },
                    {
                        "label": "missing zkp_proof",
                        "inputs": {"token": missing_zkp_token, "allow_degraded_integrity": False},
                        "decoded_proof_package": decode_token(missing_zkp_token)[0],
                        "outputs": res4b.__dict__,
                    },
                ],
            }
        )
    elif scenario_id == 5:
        print("5. PASS with old timestamp (issued 10 days ago)")
        old_date = datetime.now(timezone.utc) - timedelta(days=10)
        token5, err5 = member_generate_token(params, balance=350000, tier_id="TIER_250K", issued_at=old_date)
        res5 = _run_helper(token5, False, params)
        print(f"   Verifier: {res5.status} - {res5.reason}")
        print(f"   Tier: {_safe_label(res5.tier_label)}, issued {res5.age_human or '?'}")
        _audit_add(
            {
                "kind": "scenario",
                "id": "5",
                "description": "Old timestamp (10 days ago)",
                "member": {
                    "inputs": {"balance": 350000, "tier_id": "TIER_250K", "issued_at": old_date.isoformat()},
                    "outputs": {"token": token5, "error": err5},
                    "decoded_proof_package": decode_token(token5)[0] if token5 else None,
                },
                "verifier": {
                    "inputs": {"allow_degraded_integrity": False},
                    "outputs": res5.__dict__,
                },
            }
        )
    elif scenario_id == 6:
        demo_flow(params)
    else:
        raise ValueError(f"Unknown scenario id: {scenario_id}")
    if scenario_id != 6:
        print("\n=== scenario complete ===")


def run_scenarios(params: Dict[str, Any]) -> None:
    """Run all five PRD §7.5 test scenarios and print + audit results."""
    for i in range(1, 6):
        run_single_scenario(params, i)
        print()


# ------------------------- Demo entrypoint -------------------------

def demo_flow(params: Dict[str, Any]) -> None:
    """End-to-end: setup, member generates credential, verifier verifies."""
    print("=== Demo flow: member generates -> verifier verifies ===\n")
    balance = 350000
    tier_id = "TIER_250K"
    member_pseudonym = "member-demo"

    token, err = member_generate_token(params, balance=balance, tier_id=tier_id, member_pseudonym=member_pseudonym)
    if err:
        print(f"Member error: {err}")
        return
    print(f"Member generated token (balance={balance}, tier={tier_id})")
    print(f"Token (first 80 chars): {token[:80]}...")
    print()

    result = verifier_verify(params, token)
    print(f"Verifier: {result.status} - {result.reason}")
    print(f"Tier: {_safe_label(result.tier_label)}, issued {result.age_human}")
    print(f"Integrity: {result.integrity_status}")
    print("\n=== demo complete ===")

    _audit_add(
        {
            "kind": "demo",
            "description": "Demo flow: single member + verifier run",
            "member": {
                "inputs": {"balance": balance, "tier_id": tier_id, "member_pseudonym": member_pseudonym},
                "outputs": {"token": token, "error": err},
                "decoded_proof_package": decode_token(token)[0] if token else None,
            },
            "verifier": {
                "inputs": {"allow_degraded_integrity": False},
                "outputs": result.__dict__,
            },
        }
    )


if __name__ == "__main__":
   
    params = zkp_setup(n_bits=32)
    params["strict_range_proof"] = True
   
    print(SCENARIO_MENU)
    choice = input("Select scenario (1-6): ").strip()
    if choice in ("1", "2", "3", "4", "5", "6"):
        run_single_scenario(params, int(choice))
    else:
        print("Invalid choice. Please enter 1-6.")
   
    generate_report = input("\nGenerate audit report? (y/n): ").strip().lower()
   
    if generate_report in ("y", "yes"):
        report_path = _write_audit_report(params)
        print(f"Audit report written to {report_path}")
    else:
        print("Audit report skipped.")
