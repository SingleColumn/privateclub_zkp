# Zero-Knowledge Proof Architecture

The system implements a real cryptographic zero-knowledge proof
construction to demonstrate that a member's balance satisfies a selected
tier threshold, without revealing the balance itself.

Although the simulation executes in a single Python process, the
architecture strictly models the separation that would exist in
production:

-   The **Prover (Member device)** has access to private financial data.
-   The **Verifier (Verifier device)** has access only to:
    -   Public parameters
    -   The credential payload
    -   The proof package

Prover and verifier logic are implemented as independent functions and
must not rely on shared memory or hidden state.

------------------------------------------------------------------------

## Cryptographic Foundations

The implementation uses:

-   **Prime-order elliptic curve group:** secp256k1\
-   **Pedersen commitments** for value hiding\
-   **Schnorr proof of knowledge** to prove correct commitment opening\
-   **Bulletproof-style range proof** to prove non-negativity\
-   **Fiat--Shamir transformation** for non-interactive proofs\
-   Domain-separated hashing for transcript integrity

This construction is structurally aligned with modern confidential
transaction systems.

------------------------------------------------------------------------

## Range proof and inner-product handoff

The Bulletproofs range proof reduces to an inner-product argument (IPP).
The **range-proof → IPP handoff** is implemented as follows (aligned with
[dalek-cryptography/bulletproofs](https://github.com/dalek-cryptography/bulletproofs)):

- **Prover:** Build the IPP statement  
  `P = <l, G_vec> + <r, H'> + t_hat·Q`  
  with `H'_i = H_i·y^{-i}`, `t_hat = <l, r>`, and vectors `l`, `r` from the
  range-proof polynomial folding. The IPP proves knowledge of `(l, r)` with
  inner product `t_hat`.

- **Verifier:** After checking the first Bulletproof equation (polynomial
  commitment in G, H), verification uses a **single combined check** (mega
  check) instead of reconstructing P and calling the IPP verifier directly.
  The verifier recomputes IPP challenges from the transcript, derives
  verification scalars `(u_sq, u_inv_sq, s)` as in Dalek’s
  `InnerProductProof::verification_scalars`, and checks  
  `P_left = P_right`  
  where `P_left` includes `A + x·S`, `sumG`, **sumH over H'** (not H_vec),
  **t_hat·Q** (not t_hat·G), and the L,R terms; `P_right` is the aggregated
  commitment from the IPP proof.

------------------------------------------------------------------------

## Implementation map and validation

**Code locations:**

- **Engine** (`src/zkp/engine.py`): `zkp_setup`, `zkp_prove`, `zkp_verify`;
  Bulletproofs: `bulletproof_range_prove`, `bulletproof_range_verify`,
  `bulletproofs_mega_check`, `ipp_verification_scalars`; IPP: `_ipp_prove`,
  `_ipp_verify`. Docstrings reference Dalek’s inner_product_proof and
  RangeProof MSM where relevant.
- **Diagnostics** (`src/zkp/diagnostics/`): `debug_ipp_core.py` (IPP core
  self-test with random (a,b)); `test_step3_mega_check.py` (mega check on
  small range proofs); `debug_ipp_round.py` (round-by-round IPP checks).
- **Internal test runner** (`src/zkp/run_internal_tests.py`): runs IPP core
  self-test and Step‑3 mega-check validation.

**How to run:**

- Simulation (full prover/verifier flow):  
  `python -m src.zkp.zkp_simulation`
- Internal ZKP/diagnostics:  
  `python -m src.zkp.run_internal_tests`  
  Individual scripts:  
  `python -m src.zkp.diagnostics.debug_ipp_core`,  
  `python -m src.zkp.diagnostics.test_step3_mega_check`,  
  `python -m src.zkp.diagnostics.debug_ipp_round`

**Optional:** Set env `POF_IPP_DEBUG=1` (or `true`/`yes`) to enable
stderr debug prints inside `_ipp_prove` / `_ipp_verify`.

------------------------------------------------------------------------

## Mathematical Statement Being Proven

For a selected tier threshold `T`, the prover computes:

    v = balance − T

The prover generates a commitment:

    V = v·G + r·H

where: - `G` and `H` are independent generators, - `r` is random
blinding, - `v` is not revealed.

The prover then generates zero-knowledge proofs that:

1.  They know `(v, r)` such that `V = v·G + r·H`
2.  `v ∈ [0, 2^n_bits)`

Since `v ≥ 0`, it follows that:

    balance ≥ T

No information about the exact balance is disclosed.

------------------------------------------------------------------------

## Public Setup

``` python
params = zkp_setup(n_bits=32)
```

Returns:

-   Curve parameters
-   Base generators `G`, `H`
-   Independent generator vectors for Bulletproofs
-   Domain separator constants
-   Range bit length (`n_bits`, must be power of two)

No private data is included in setup.

------------------------------------------------------------------------

## Prover Function (Member Device)

``` python
proof_package = zkp_prove(
    params,
    balance: int,
    threshold: int,
    credential_payload: dict
)
```

### Inputs

-   `balance` --- private witness (never revealed)
-   `threshold` --- selected tier threshold
-   `credential_payload` --- includes:
    -   tier identifier
    -   timestamp
    -   pseudonymous member identifier
    -   device integrity status

### Required Behavior

1.  Compute:

```{=html}
<!-- -->
```
    credential_payload_hash = H(canonical_json(credential_payload))

2.  Compute context binding:

```{=html}
<!-- -->
```
    context = H("POF_CTX_V1" || credential_payload_hash || threshold)

3.  Compute:

```{=html}
<!-- -->
```
    v = balance − threshold

4.  Generate:
    -   Pedersen commitment to `v`
    -   Schnorr proof of knowledge of `(v, r)`
    -   Bulletproof range proof that `v ∈ [0, 2^n_bits)`

### Output

An opaque `proof_package` containing:

-   Commitment
-   Schnorr opening proof
-   Bulletproof range proof
-   Metadata:
    -   threshold
    -   credential payload hash
    -   range bit size

The proof must not reveal: - The exact balance - The value `v` -
Commitment randomness

------------------------------------------------------------------------

## 7.2.5 Verifier Function (Verifier Device)

``` python
is_valid = zkp_verify(
    params,
    threshold: int,
    credential_payload: dict,
    proof_package: dict
)
```

### Verification Steps

1.  Recompute:

```{=html}
<!-- -->
```
    credential_payload_hash = H(canonical_json(credential_payload))

2.  Recompute context binding.

3.  Validate:

    -   Schnorr opening proof
    -   Bulletproof range proof
    -   Consistency of threshold
    -   Consistency of credential payload hash
    -   Domain separation

Returns:

-   `True` if valid
-   `False` otherwise

If valid, verifier can conclude:

    balance ≥ threshold

without learning the balance.

------------------------------------------------------------------------

## 7.2.6 Transcript Binding and Replay Protection

All Fiat--Shamir challenges are derived from:

    domain_separator ||
    commitments ||
    public_parameters ||
    threshold ||
    credential_payload_hash ||
    context

This prevents:

-   Replay across credentials
-   Replay across thresholds
-   Cross-protocol attacks
-   Tier substitution attacks

Each proof is cryptographically bound to: - A specific tier threshold -
A specific credential payload - A specific protocol version

------------------------------------------------------------------------

## 7.2.7 Simulation Clarification

The current implementation runs prover and verifier code within one
process for development purposes.

However:

-   Prover and verifier functions are logically independent.
-   No shared state is used.
-   Proof validity depends solely on provided inputs.

This preserves architectural realism and allows future migration to: -
Separate mobile client and verifier apps - Different machines - Remote
verification services

------------------------------------------------------------------------

## 7.2.8 Implementation Status Disclaimer

This implementation is:

-   Structurally aligned with modern zero-knowledge systems
-   Based on real cryptographic primitives
-   Suitable for architectural validation and prototyping

It is not yet:

-   Constant-time hardened
-   Formally audited
-   Production-grade cryptography

Production deployment would require:

-   Independent cryptographic review
-   Library hardening
-   Security audit
-   Formal threat modeling
