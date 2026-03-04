"""
engine.py — Proof-of-Funds ZKP engine (aligned with zkp_architecture.md)

Implements:
- Prime-order elliptic curve group: secp256k1
- Pedersen commitment to hidden v
- Schnorr proof of knowledge of opening (v, r)
- Bulletproofs-style range proof: v ∈ [0, 2^n_bits)

Mathematical statement:
    v = balance - threshold
    Prove v ∈ [0, 2^n_bits)  ⇒  balance ≥ threshold

Binding per zkp_architecture.md:
- credential_payload_hash = H(canonical_json(credential_payload))
- context = H("POF_CTX_V1" || credential_payload_hash || threshold)
- Fiat–Shamir challenges derived from transcript that includes context, commitment, parameters.

WARNING:
- Prototype/reference code. Not constant-time, not audited, not production hardened.
- Generator derivation is simplified hash-to-scalar then multiply-by-basepoint.

Dependency:
    pip install ecdsa
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple
import hashlib
import json
import os
import secrets

from ecdsa.curves import SECP256k1
from ecdsa.ellipticcurve import PointJacobi, Point

Curve = SECP256k1.curve
G_BASE: PointJacobi = SECP256k1.generator
ORDER: int = SECP256k1.order

DOMAIN_ZKP = b"POF_ZKP_V1"
DOMAIN_CTX = b"POF_CTX_V1"
DOMAIN_GEN = b"POF_GEN_V1"

# Set POF_IPP_DEBUG=1 to enable stderr logging in _ipp_prove / _ipp_verify (n=2 case).
_IPP_DEBUG = os.environ.get("POF_IPP_DEBUG", "").strip().lower() in ("1", "true", "yes")


# ------------------------- Utilities -------------------------

def _int_to_bytes(x: int, length: int = 32) -> bytes:
    return x.to_bytes(length, "big", signed=False)

def _hash256(data: bytes) -> bytes:
    return hashlib.sha256(data).digest()

def _canonical_json(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")

def _hash_to_scalar(*chunks: bytes, dst: bytes) -> int:
    h = hashlib.sha256(dst)
    for c in chunks:
        h.update(c)
    return int.from_bytes(h.digest(), "big") % ORDER

def _rand_scalar() -> int:
    return secrets.randbelow(ORDER - 1) + 1

def _scalar(x: int) -> int:
    return x % ORDER

def _point_mul(P: PointJacobi, k: int) -> PointJacobi:
    return P * _scalar(k)

def _point_add(P: PointJacobi, Q: PointJacobi) -> PointJacobi:
    return P + Q

def _point_sub(P: PointJacobi, Q: PointJacobi) -> PointJacobi:
    return P + (-Q)

def _point_to_bytes(P: PointJacobi) -> bytes:
    Pa = P.to_affine()
    x = int(Pa.x())
    y = int(Pa.y())
    prefix = b"\x02" if (y % 2 == 0) else b"\x03"
    return prefix + _int_to_bytes(x, 32)

def decompress_point(comp: bytes) -> PointJacobi:
    if len(comp) != 33:
        raise ValueError("invalid compressed point length")
    prefix = comp[0]
    if prefix not in (2, 3):
        raise ValueError("invalid compressed point prefix")
    x = int.from_bytes(comp[1:], "big")

    p = Curve.p()
    a = Curve.a()
    b = Curve.b()

    rhs = (pow(x, 3, p) + (a * x) + b) % p
    y = pow(rhs, (p + 1) // 4, p)  # secp256k1 prime p % 4 == 3
    if (y % 2 == 0 and prefix == 3) or (y % 2 == 1 and prefix == 2):
        y = (-y) % p

    P_aff = Point(Curve, x, y, ORDER)
    return PointJacobi.from_affine(P_aff)

def _powers(base: int, n: int) -> List[int]:
    out = [1]
    for _ in range(1, n):
        out.append((out[-1] * base) % ORDER)
    return out

def _two_powers(n: int) -> List[int]:
    out = [1]
    for _ in range(1, n):
        out.append((out[-1] * 2) % ORDER)
    return out

def _inner_product(a: List[int], b: List[int]) -> int:
    s = 0
    for x, y in zip(a, b):
        s = (s + x * y) % ORDER
    return s

def _vector_add(a: List[int], b: List[int]) -> List[int]:
    return [(_scalar(x + y)) for x, y in zip(a, b)]

def _vector_sub(a: List[int], b: List[int]) -> List[int]:
    return [(_scalar(x - y)) for x, y in zip(a, b)]

def _vector_mul(a: List[int], b: List[int]) -> List[int]:
    return [(_scalar(x * y)) for x, y in zip(a, b)]

def _vector_scalar_mul(a: List[int], k: int) -> List[int]:
    return [(_scalar(x * k)) for x in a]

def _multi_exp(points: List[PointJacobi], scalars: List[int]) -> PointJacobi:
    acc = None
    for P, k in zip(points, scalars):
        term = _point_mul(P, k)
        acc = term if acc is None else (acc + term)
    if acc is None:
        raise ValueError("empty multiexp")
    return acc

def _vector_commit(G_vec: List[PointJacobi], H_vec: List[PointJacobi], a: List[int], b: List[int]) -> PointJacobi:
    return _point_add(_multi_exp(G_vec, a), _multi_exp(H_vec, b))

def _challenge_scalar(transcript: List[bytes], dst: bytes) -> int:
    return _hash_to_scalar(*transcript, dst=dst)


# ------------------ Generator derivation ------------------

def _derive_generator(tag: bytes) -> PointJacobi:
    s = _hash_to_scalar(tag, dst=DOMAIN_GEN)
    if s == 0:
        s = 1
    return _point_mul(G_BASE, s)

def _derive_generators(prefix: bytes, n: int) -> List[PointJacobi]:
    return [_derive_generator(prefix + b":" + str(i).encode("utf-8")) for i in range(n)]


# ------------------ Pedersen commitment ------------------

def pedersen_commit(G: PointJacobi, H: PointJacobi, v: int, r: int) -> PointJacobi:
    return _point_add(_point_mul(G, v), _point_mul(H, r))


# ------------------ Schnorr opening proof ------------------

@dataclass
class SchnorrOpeningProof:
    R: bytes
    s_v: int
    s_r: int

def schnorr_prove_opening(G: PointJacobi, H: PointJacobi, C: PointJacobi, v: int, r: int, context: bytes) -> SchnorrOpeningProof:
    k_v = _rand_scalar()
    k_r = _rand_scalar()
    R_point = _point_add(_point_mul(G, k_v), _point_mul(H, k_r))

    c = _hash_to_scalar(
        DOMAIN_ZKP,
        _point_to_bytes(G),
        _point_to_bytes(H),
        _point_to_bytes(C),
        _point_to_bytes(R_point),
        context,
        dst=b"POF_SCHNORR_OPEN_V1",
    )

    s_v = (k_v + c * (v % ORDER)) % ORDER
    s_r = (k_r + c * (r % ORDER)) % ORDER
    return SchnorrOpeningProof(R=_point_to_bytes(R_point), s_v=s_v, s_r=s_r)

def schnorr_verify_opening(G: PointJacobi, H: PointJacobi, C: PointJacobi, proof: SchnorrOpeningProof, context: bytes) -> bool:
    try:
        R_point = decompress_point(proof.R)
        c = _hash_to_scalar(
            DOMAIN_ZKP,
            _point_to_bytes(G),
            _point_to_bytes(H),
            _point_to_bytes(C),
            _point_to_bytes(R_point),
            context,
            dst=b"POF_SCHNORR_OPEN_V1",
        )
        left = _point_add(_point_mul(G, proof.s_v), _point_mul(H, proof.s_r))
        right = _point_add(R_point, _point_mul(C, c))
        return _point_to_bytes(left) == _point_to_bytes(right)
    except Exception:
        return False


# ------------------ Bulletproofs range proof ------------------

@dataclass
class InnerProductProof:
    L: List[bytes]
    R: List[bytes]
    a: int
    b: int

@dataclass
class BulletproofRangeProof:
    A: bytes
    S: bytes
    T1: bytes
    T2: bytes
    tau_x: int
    mu: int
    t_hat: int
    ipp: InnerProductProof

def _ipp_prove(G_vec: List[PointJacobi], H_vec: List[PointJacobi], Q: PointJacobi, P: PointJacobi,
               a: List[int], b: List[int], transcript: List[bytes]) -> InnerProductProof:
    n = len(a)
    if n == 1:
        return InnerProductProof(L=[], R=[], a=a[0] % ORDER, b=b[0] % ORDER)

    n2 = n // 2
    aL, aR = a[:n2], a[n2:]
    bL, bR = b[:n2], b[n2:]
    GL, GR = G_vec[:n2], G_vec[n2:]
    HL, HR = H_vec[:n2], H_vec[n2:]

    cL = _inner_product(aL, bR)
    cR = _inner_product(aR, bL)

    L_point = _point_add(_vector_commit(GR, HL, aL, bR), _point_mul(Q, cL))
    R_point = _point_add(_vector_commit(GL, HR, aR, bL), _point_mul(Q, cR))

    transcript2 = transcript + [_point_to_bytes(L_point), _point_to_bytes(R_point)]
    x = _challenge_scalar(transcript2, dst=b"POF_BP_IPP_CHAL_V1")
    x_inv = pow(x, ORDER - 2, ORDER)

    a_new = [(_scalar(aL[i] * x + aR[i] * x_inv)) for i in range(n2)]
    b_new = [(_scalar(bL[i] * x_inv + bR[i] * x)) for i in range(n2)]

    G_new = [_point_add(_point_mul(GL[i], x_inv), _point_mul(GR[i], x)) for i in range(n2)]
    H_new = [_point_add(_point_mul(HL[i], x), _point_mul(HR[i], x_inv)) for i in range(n2)]

    P_new = _point_add(
        _point_add(_point_mul(L_point, (x * x) % ORDER), P),
        _point_mul(R_point, (x_inv * x_inv) % ORDER),
    )

    if _IPP_DEBUG and n == 2:
        try:
            import sys
            print("=== IPP PROVE (n=2) ===", file=sys.stderr)
            print("  L_point:", _point_to_bytes(L_point).hex(), file=sys.stderr)
            print("  R_point:", _point_to_bytes(R_point).hex(), file=sys.stderr)
            print("  x:", x, file=sys.stderr)
            print("  P_new:", _point_to_bytes(P_new).hex(), file=sys.stderr)
        except Exception:
            pass

    sub = _ipp_prove(G_new, H_new, Q, P_new, a_new, b_new, transcript2)
    return InnerProductProof(
        L=[_point_to_bytes(L_point)] + sub.L,
        R=[_point_to_bytes(R_point)] + sub.R,
        a=sub.a,
        b=sub.b,
    )

def _ipp_verify(G_vec: List[PointJacobi], H_vec: List[PointJacobi], Q: PointJacobi, P: PointJacobi,
                proof: InnerProductProof, transcript: List[bytes]) -> bool:
    try:
        n = len(G_vec)
        logn = len(proof.L)
        if n != 2 ** logn:
            return False

        G_curr = G_vec[:]
        H_curr = H_vec[:]
        P_curr = P
        transcript_curr = transcript[:]

        for i in range(logn):
            L_i = decompress_point(proof.L[i])
            R_i = decompress_point(proof.R[i])
            transcript_curr = transcript_curr + [_point_to_bytes(L_i), _point_to_bytes(R_i)]

            x = _challenge_scalar(transcript_curr, dst=b"POF_BP_IPP_CHAL_V1")
            x_inv = pow(x, ORDER - 2, ORDER)

            P_curr = _point_add(
                _point_add(_point_mul(L_i, (x * x) % ORDER), P_curr),
                _point_mul(R_i, (x_inv * x_inv) % ORDER),
            )

            n2 = len(G_curr) // 2
            GL, GR = G_curr[:n2], G_curr[n2:]
            HL, HR = H_curr[:n2], H_curr[n2:]
            G_curr = [_point_add(_point_mul(GL[j], x_inv), _point_mul(GR[j], x)) for j in range(n2)]
            H_curr = [_point_add(_point_mul(HL[j], x), _point_mul(HR[j], x_inv)) for j in range(n2)]

        if len(G_curr) != 1 or len(H_curr) != 1:
            return False

        a = proof.a % ORDER
        b = proof.b % ORDER
        rhs_with_q = _point_add(
            _point_add(_point_mul(G_curr[0], a), _point_mul(H_curr[0], b)),
            _point_mul(Q, (a * b) % ORDER),
        )
        rhs_no_q = _point_add(_point_mul(G_curr[0], a), _point_mul(H_curr[0], b))

        if _IPP_DEBUG and n == 2 and logn == 1:
            try:
                import sys
                print("=== IPP VERIFY (n=2) ===", file=sys.stderr)
                print("  L_i:", _point_to_bytes(L_i).hex(), file=sys.stderr)
                print("  R_i:", _point_to_bytes(R_i).hex(), file=sys.stderr)
                print("  x:", x, file=sys.stderr)
                print("  P_curr:", _point_to_bytes(P_curr).hex(), file=sys.stderr)
                print("  G_final:", _point_to_bytes(G_curr[0]).hex(), file=sys.stderr)
                print("  H_final:", _point_to_bytes(H_curr[0]).hex(), file=sys.stderr)
                print("  a:", a, file=sys.stderr)
                print("  b:", b, file=sys.stderr)
                print("  rhs_with_q:", _point_to_bytes(rhs_with_q).hex(), file=sys.stderr)
                print("  rhs_no_q:", _point_to_bytes(rhs_no_q).hex(), file=sys.stderr)
                print("  eq_with_q:", _point_to_bytes(P_curr) == _point_to_bytes(rhs_with_q), file=sys.stderr)
                print("  eq_no_q:", _point_to_bytes(P_curr) == _point_to_bytes(rhs_no_q), file=sys.stderr)
            except Exception:
                pass

        return _point_to_bytes(P_curr) == _point_to_bytes(rhs_with_q)
    except Exception:
        return False


def ipp_verification_scalars(
    proof: InnerProductProof,
    n: int,
    transcript: List[bytes],
) -> Tuple[List[int], List[int], List[int]]:
    """
    Recompute IPP Fiat–Shamir challenges from transcript + L/R, then derive
    u_sq[i] = u_i^2, u_inv_sq[i] = u_i^{-2}, and the s vector as in Dalek's
    InnerProductProof::verification_scalars. Used for Dalek-style aggregated
    MSM verification (e.g. bulletproofs_mega_check) instead of direct _ipp_verify.

    Reference: dalek-cryptography/bulletproofs src/inner_product_proof.rs.

    Returns (u_sq, u_inv_sq, s). Caller uses:
      P_expect = (a*b)*Q + sum_i (a*s_i)*G_i + sum_i (b*s_rev_i)*H_i
                + sum_j (-u_sq[j])*L_j + sum_j (-u_inv_sq[j])*R_j
    where s_rev = s reversed (H side uses s in reverse order per Dalek).
    """
    lg_n = len(proof.L)
    if lg_n >= 32 or n != (1 << lg_n):
        raise ValueError("ipp_verification_scalars: invalid n or proof length")

    transcript_curr = list(transcript)
    challenges: List[int] = []
    for i in range(lg_n):
        transcript_curr.append(proof.L[i])
        transcript_curr.append(proof.R[i])
        u = _challenge_scalar(transcript_curr, dst=b"POF_BP_IPP_CHAL_V1")
        challenges.append(_scalar(u))

    challenges_inv = [pow(u, ORDER - 2, ORDER) for u in challenges]
    allinv = 1
    for u_inv in challenges_inv:
        allinv = (allinv * u_inv) % ORDER

    u_sq = [_scalar(u * u) for u in challenges]
    u_inv_sq = [_scalar(ui * ui) for ui in challenges_inv]

    s: List[int] = [_scalar(allinv)]
    for i in range(1, n):
        lg_i = (i).bit_length() - 1
        k = 1 << lg_i
        idx = (lg_n - 1) - lg_i
        s.append(_scalar(s[i - k] * u_sq[idx]))

    return (u_sq, u_inv_sq, s)


def bulletproofs_mega_check(
    params: Dict[str, Any],
    V: PointJacobi,
    proof: BulletproofRangeProof,
    context: bytes,
    transcript: List[bytes],
    y: int,
    z: int,
    x: int,
) -> bool:
    """
    Dalek-style combined MSM check (cf. RangeProof verification in range_proof.rs):
    recompute IPP verification scalars and check P_left == P_right where
      P_left  = A + x*S + sumG + sumH + t_hat*Q - mu*H + sum(u_sq*L) + sum(u_inv_sq*R)
      P_right = (a*b)*Q + sum(a*s_i)*G_i + sum(b*s_rev_i)*H_prime_i
    Uses ipp_verification_scalars instead of direct _ipp_verify. Returns True iff equal.
    """
    try:
        G_vec: List[PointJacobi] = params["G_vec"]
        H_vec: List[PointJacobi] = params["H_vec"]
        G: PointJacobi = params["G"]
        H: PointJacobi = params["H"]
        Q: PointJacobi = params["Q"]
        n = len(G_vec)

        A_point = decompress_point(proof.A)
        S_point = decompress_point(proof.S)

        y_pows = _powers(y, n)
        two_pows = _two_powers(n)
        z2 = (z * z) % ORDER

        sumG = _multi_exp(G_vec, [(_scalar(-z))] * n)
        Hy = [_scalar(z * y_pows[i] + z2 * two_pows[i]) for i in range(n)]
        y_inv = pow(y, ORDER - 2, ORDER)
        y_inv_pows = _powers(y_inv, n)
        H_prime = [_point_mul(H_vec[i], y_inv_pows[i]) for i in range(n)]
        sumH = _multi_exp(H_prime, Hy)

        a_final = _scalar(proof.ipp.a)
        b_final = _scalar(proof.ipp.b)
        u_sq, u_inv_sq, s = ipp_verification_scalars(proof.ipp, n, transcript)
        s_rev = list(reversed(s))

        P_left = _point_add(A_point, _point_mul(S_point, x))
        P_left = _point_add(P_left, sumG)
        P_left = _point_add(P_left, sumH)
        P_left = _point_add(P_left, _point_mul(Q, proof.t_hat))
        P_left = _point_sub(P_left, _point_mul(H, proof.mu))
        for j in range(len(proof.ipp.L)):
            L_j = decompress_point(proof.ipp.L[j])
            R_j = decompress_point(proof.ipp.R[j])
            P_left = _point_add(P_left, _point_mul(L_j, u_sq[j]))
            P_left = _point_add(P_left, _point_mul(R_j, u_inv_sq[j]))

        P_right = _point_mul(Q, _scalar(a_final * b_final))
        P_right = _point_add(P_right, _multi_exp(G_vec, [_scalar(a_final * si) for si in s]))
        P_right = _point_add(P_right, _multi_exp(H_prime, [_scalar(b_final * s_rev[j]) for j in range(n)]))

        return _point_to_bytes(P_left) == _point_to_bytes(P_right)
    except Exception:
        return False

def bulletproof_range_prove(
    params: Dict[str, Any],
    V: PointJacobi,
    v: int,
    r: int,
    n_bits: int,
    context: bytes,
) -> BulletproofRangeProof:
    """
    Bulletproofs range proof: prove v in [0, 2^n_bits). Commitment P = <l,G> + <r,H'> + t_hat*Q
    with H' = H_i * y^{-i}; IPP proves knowledge of (l, r) with <l,r> = t_hat. See Dalek range_proof.
    """
    G_vec: List[PointJacobi] = params["G_vec"]
    H_vec: List[PointJacobi] = params["H_vec"]
    G: PointJacobi = params["G"]
    H: PointJacobi = params["H"]
    Q: PointJacobi = params["Q"]

    n = n_bits

    aL = [((v >> i) & 1) % ORDER for i in range(n)]
    aR = [(_scalar(x - 1)) for x in aL]

    alpha = _rand_scalar()
    A_point = _point_add(_vector_commit(G_vec, H_vec, aL, aR), _point_mul(H, alpha))

    sL = [_rand_scalar() for _ in range(n)]
    sR = [_rand_scalar() for _ in range(n)]
    rho = _rand_scalar()
    S_point = _point_add(_vector_commit(G_vec, H_vec, sL, sR), _point_mul(H, rho))

    transcript = [
        DOMAIN_ZKP,
        b"BP_RANGE_V1",
        _point_to_bytes(G),
        _point_to_bytes(H),
        _point_to_bytes(Q),
        _point_to_bytes(V),
        _point_to_bytes(A_point),
        _point_to_bytes(S_point),
        context,
    ]
    y = _challenge_scalar(transcript, dst=b"POF_BP_Y_V1")
    z = _challenge_scalar(transcript + [_int_to_bytes(y)], dst=b"POF_BP_Z_V1")

    y_pows = _powers(y, n)
    two_pows = _two_powers(n)
    z_vec = [z] * n
    z2 = (z * z) % ORDER

    l0 = _vector_sub(aL, z_vec)
    l1 = sL[:]

    r0 = _vector_add(aR, z_vec)
    r0 = _vector_mul(r0, y_pows)
    r0 = _vector_add(r0, _vector_scalar_mul(two_pows, z2))
    r1 = _vector_mul(sR, y_pows)

    t1 = (_inner_product(l1, r0) + _inner_product(l0, r1)) % ORDER
    t2 = _inner_product(l1, r1)

    tau1 = _rand_scalar()
    tau2 = _rand_scalar()
    T1_point = _point_add(_point_mul(G, t1), _point_mul(H, tau1))
    T2_point = _point_add(_point_mul(G, t2), _point_mul(H, tau2))

    transcript2 = transcript + [
        _point_to_bytes(T1_point),
        _point_to_bytes(T2_point),
        _int_to_bytes(y),
        _int_to_bytes(z),
    ]
    x = _challenge_scalar(transcript2, dst=b"POF_BP_X_V1")

    l = _vector_add(l0, _vector_scalar_mul(l1, x))
    r_vec = _vector_add(r0, _vector_scalar_mul(r1, x))
    t_hat = _inner_product(l, r_vec)

    tau_x = (tau2 * (x * x % ORDER) + tau1 * x + z2 * (r % ORDER)) % ORDER
    mu = (alpha + rho * x) % ORDER

    y_inv = pow(y, ORDER - 2, ORDER)
    y_inv_pows = _powers(y_inv, n)
    H_prime = [_point_mul(H_vec[i], y_inv_pows[i]) for i in range(n)]
    # Per Bulletproofs: P = <l, G> + <r, H'> + t_hat*Q with t_hat = <l, r> (r = r_vec, not r')
    P_point = _multi_exp(G_vec, l)
    P_point = _point_add(P_point, _multi_exp(H_prime, r_vec))
    P_point = _point_add(P_point, _point_mul(Q, t_hat))

    ipp = _ipp_prove(G_vec, H_prime, Q, P_point, l, r_vec, transcript2 + [_int_to_bytes(x)])

    return BulletproofRangeProof(
        A=_point_to_bytes(A_point),
        S=_point_to_bytes(S_point),
        T1=_point_to_bytes(T1_point),
        T2=_point_to_bytes(T2_point),
        tau_x=tau_x,
        mu=mu,
        t_hat=t_hat,
        ipp=ipp,
    )

def bulletproof_range_verify(
    params: Dict[str, Any],
    V: PointJacobi,
    n_bits: int,
    proof: BulletproofRangeProof,
    context: bytes,
) -> bool:
    """
    Verify Bulletproof range proof: (1) first equation t_hat*G + tau_x*H = x*T1 + x^2*T2 + z^2*V + delta*G;
    (2) bulletproofs_mega_check (Dalek-style MSM over A, S, G, H, Q, G_vec, H_prime, L, R). See Dalek range_proof.
    """
    try:
        G_vec: List[PointJacobi] = params["G_vec"]
        H_vec: List[PointJacobi] = params["H_vec"]
        G: PointJacobi = params["G"]
        H: PointJacobi = params["H"]
        Q: PointJacobi = params["Q"]

        n = n_bits
        A_point = decompress_point(proof.A)
        S_point = decompress_point(proof.S)
        T1_point = decompress_point(proof.T1)
        T2_point = decompress_point(proof.T2)

        transcript = [
            DOMAIN_ZKP,
            b"BP_RANGE_V1",
            _point_to_bytes(G),
            _point_to_bytes(H),
            _point_to_bytes(Q),
            _point_to_bytes(V),
            _point_to_bytes(A_point),
            _point_to_bytes(S_point),
            context,
        ]
        y = _challenge_scalar(transcript, dst=b"POF_BP_Y_V1")
        z = _challenge_scalar(transcript + [_int_to_bytes(y)], dst=b"POF_BP_Z_V1")

        y_pows = _powers(y, n)
        two_pows = _two_powers(n)
        z2 = (z * z) % ORDER
        z3 = (z2 * z) % ORDER

        transcript2 = transcript + [
            _point_to_bytes(T1_point),
            _point_to_bytes(T2_point),
            _int_to_bytes(y),
            _int_to_bytes(z),
        ]
        x = _challenge_scalar(transcript2, dst=b"POF_BP_X_V1")

        sum_y = sum(y_pows) % ORDER
        sum_2 = sum(two_pows) % ORDER
        delta = (((z - z2) % ORDER) * sum_y - (z3 * sum_2) % ORDER) % ORDER

        left = _point_add(_point_mul(G, proof.t_hat), _point_mul(H, proof.tau_x))

        right = _point_add(_point_mul(T1_point, x), _point_mul(T2_point, (x * x) % ORDER))
        right = _point_add(right, _point_mul(V, z2))
        right = _point_add(right, _point_mul(G, delta))

        if _point_to_bytes(left) != _point_to_bytes(right):
            return False

        ipp_transcript = transcript2 + [_int_to_bytes(x)]
        return bulletproofs_mega_check(
            params,
            V,
            proof,
            context,
            transcript=ipp_transcript,
            y=y,
            z=z,
            x=x,
        )
    except Exception:
        return False


# ------------------ Engine wrapper + PRD aliases ------------------

class ZKPEngine:
    @staticmethod
    def setup(n_bits: int = 32) -> Dict[str, Any]:
        if n_bits <= 0 or (n_bits & (n_bits - 1)) != 0:
            raise ValueError("n_bits must be a power of two (e.g., 32, 64, 128)")

        G = G_BASE
        H = _derive_generator(b"H")
        Q = _derive_generator(b"Q")

        G_vec = _derive_generators(b"G_vec", n_bits)
        H_vec = _derive_generators(b"H_vec", n_bits)

        return {
            "curve": "secp256k1",
            "order": ORDER,
            "G": G,
            "H": H,
            "Q": Q,
            "n_bits": n_bits,
            "G_vec": G_vec,
            "H_vec": H_vec,
            "domain_separator": DOMAIN_ZKP,
        }

    @staticmethod
    def prove(params: Dict[str, Any], balance: int, threshold: int, credential_payload: Dict[str, Any]) -> Dict[str, Any]:
        if balance < 0 or threshold < 0:
            raise ValueError("balance and threshold must be non-negative integers")

        n_bits = int(params["n_bits"])
        v = balance - threshold
        if v < 0:
            raise ValueError("insufficient funds for chosen tier (balance < threshold)")
        if v >= (1 << n_bits):
            raise ValueError("value too large for configured n_bits")

        credential_payload_hash = _hash256(_canonical_json(credential_payload))
        context = _hash256(DOMAIN_CTX + b"|" + credential_payload_hash + b"|" + _int_to_bytes(threshold, 32))

        G: PointJacobi = params["G"]
        H: PointJacobi = params["H"]

        r = _rand_scalar()
        V = pedersen_commit(G, H, v, r)

        open_proof = schnorr_prove_opening(G, H, V, v, r, context=context)
        bp = bulletproof_range_prove(params, V, v, r, n_bits=n_bits, context=context)

        return {
            "commitment": _point_to_bytes(V).hex(),
            "schnorr_opening": {"R": open_proof.R.hex(), "s_v": int(open_proof.s_v), "s_r": int(open_proof.s_r)},
            "bulletproof": {
                "A": bp.A.hex(),
                "S": bp.S.hex(),
                "T1": bp.T1.hex(),
                "T2": bp.T2.hex(),
                "tau_x": int(bp.tau_x),
                "mu": int(bp.mu),
                "t_hat": int(bp.t_hat),
                "ipp": {
                    "L": [x.hex() for x in bp.ipp.L],
                    "R": [x.hex() for x in bp.ipp.R],
                    "a": int(bp.ipp.a),
                    "b": int(bp.ipp.b),
                },
            },
            "meta": {
                "n_bits": n_bits,
                "threshold": int(threshold),
                "credential_payload_hash": credential_payload_hash.hex(),
                "context_hash": context.hex(),
                "domain_separator": DOMAIN_ZKP.decode("utf-8", errors="ignore"),
            },
        }

    @staticmethod
    def verify(params: Dict[str, Any], threshold: int, credential_payload: Dict[str, Any], proof_package: Dict[str, Any]) -> bool:
        try:
            meta = proof_package.get("meta", {})
            if int(meta.get("threshold", threshold)) != int(threshold):
                return False

            credential_payload_hash = _hash256(_canonical_json(credential_payload))
            if meta.get("credential_payload_hash") != credential_payload_hash.hex():
                return False

            context = _hash256(DOMAIN_CTX + b"|" + credential_payload_hash + b"|" + _int_to_bytes(threshold, 32))

            G: PointJacobi = params["G"]
            H: PointJacobi = params["H"]

            V = decompress_point(bytes.fromhex(proof_package["commitment"]))

            sp = proof_package["schnorr_opening"]
            open_proof = SchnorrOpeningProof(
                R=bytes.fromhex(sp["R"]),
                s_v=int(sp["s_v"]) % ORDER,
                s_r=int(sp["s_r"]) % ORDER,
            )
            if not schnorr_verify_opening(G, H, V, open_proof, context=context):
                return False

            bpj = proof_package["bulletproof"]
            ippj = bpj["ipp"]
            ipp = InnerProductProof(
                L=[bytes.fromhex(x) for x in ippj["L"]],
                R=[bytes.fromhex(x) for x in ippj["R"]],
                a=int(ippj["a"]) % ORDER,
                b=int(ippj["b"]) % ORDER,
            )
            bp = BulletproofRangeProof(
                A=bytes.fromhex(bpj["A"]),
                S=bytes.fromhex(bpj["S"]),
                T1=bytes.fromhex(bpj["T1"]),
                T2=bytes.fromhex(bpj["T2"]),
                tau_x=int(bpj["tau_x"]) % ORDER,
                mu=int(bpj["mu"]) % ORDER,
                t_hat=int(bpj["t_hat"]) % ORDER,
                ipp=ipp,
            )
            return bulletproof_range_verify(params, V, n_bits=int(params["n_bits"]), proof=bp, context=context)
        except Exception:
            return False


def zkp_setup(n_bits: int = 32) -> Dict[str, Any]:
    return ZKPEngine.setup(n_bits=n_bits)

def zkp_prove(params: Dict[str, Any], balance: int, threshold: int, credential_payload: Dict[str, Any]) -> Dict[str, Any]:
    return ZKPEngine.prove(params, balance=balance, threshold=threshold, credential_payload=credential_payload)

def zkp_verify(params: Dict[str, Any], threshold: int, credential_payload: Dict[str, Any], proof_package: Dict[str, Any]) -> bool:
    return ZKPEngine.verify(params, threshold=threshold, credential_payload=credential_payload, proof_package=proof_package)