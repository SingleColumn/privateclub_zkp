## ZKP Engine PRD and Normative Specification

This document extends `zkp_architecture.md` and `prd.md` with **normative,
interoperability‑oriented details** for the proof‑of‑funds ZKP engine. Its
goal is to allow an independent implementer (or alternative coding
assistant) to build a **drop‑in compatible** engine that:

- Implements the same mathematical statement and security properties.
- Uses the same Fiat–Shamir transcripts, domain separators, and challenges.
- Uses the same commitment and proof encodings.
- Produces and verifies proof packages that interoperate at the
  **serialization level**.

Where there is any ambiguity, **this document plus `zkp_architecture.md`
are authoritative** for the Python reference implementation in `src/zkp/`.

------------------------------------------------------------------------

## 1. Scope and dependencies

- **Curve:** secp256k1 (`ecdsa.SECP256k1` in the reference implementation).
- **Group operations:** standard scalar multiplication and point addition
  in the prime‑order subgroup of secp256k1.
- **Hash function:** SHA‑256.
- **Encoding of scalars:** unsigned big‑endian fixed‑length 32‑byte values
  when serialized to bytes (see `_int_to_bytes`).
- **Encoding of points:** compressed secp256k1 points (33 bytes) with
  prefix `0x02`/`0x03` according to the parity of `y` (see `_point_to_bytes`
  and `decompress_point`).

The high‑level statement, prover/verifier APIs, and range‑proof/IPP
handoff are described in `zkp_architecture.md` and not repeated here.

------------------------------------------------------------------------

## 2. Canonical JSON and credential payload hashing

All bindings to the external credential payload use a **canonical JSON**
encoding and a SHA‑256 hash.

- **Canonical JSON function** (reference: `_canonical_json` in `engine.py`):

  ```python
  json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")
  ```

  - `sort_keys=True` (lexicographic key order).
  - `separators=(",", ":")` (no spaces after commas or colons).
  - UTF‑8 encoding of the resulting string.

- **Credential payload hash**:

  ```text
  credential_payload_hash = SHA256(canonical_json(credential_payload))
  ```

  - Output is 32 bytes; when serialized in JSON it is represented as a
    **lower‑case hex string**.

Any independent implementation **MUST** reproduce this exact canonical
JSON behavior and hashing to interoperate.

------------------------------------------------------------------------

## 3. Domain separators and challenge derivation

All Fiat–Shamir challenges are derived from a **domain‑separated**
SHA‑256‑based hash‑to‑scalar function:

```python
def hash_to_scalar(chunks: List[bytes], dst: bytes) -> int:
    h = sha256(dst)
    for c in chunks:
        h.update(c)
    return int.from_bytes(h.digest(), "big") % ORDER
```

In the reference code:

- `ORDER` = secp256k1 subgroup order.
- Helper: `_hash_to_scalar(*chunks, dst=...)` and
  `_challenge_scalar(transcript, dst)` which simply calls `_hash_to_scalar`
  with `*transcript`.

### 3.1 Global domain constants

All implementations **MUST** use the exact byte strings:

- `DOMAIN_ZKP = b"POF_ZKP_V1"`
- `DOMAIN_CTX = b"POF_CTX_V1"`
- `DOMAIN_GEN = b"POF_GEN_V1"`

Additional range‑proof/IPP specific destination tags:

- `b"POF_SCHNORR_OPEN_V1"` — Schnorr opening proof for Pedersen
  commitment.
- `b"POF_BP_IPP_CHAL_V1"` — IPP challenges `x` / `u_i`.
- `b"POF_BP_Y_V1"` — Bulletproofs challenge `y`.
- `b"POF_BP_Z_V1"` — Bulletproofs challenge `z`.
- `b"POF_BP_X_V1"` — Bulletproofs challenge `x` for the quadratic
  polynomial.

These tags are **prefix inputs** to SHA‑256, not part of the transcript
array.

### 3.2 Context binding

Context binds the proof to the credential payload and threshold:

```text
context = SHA256(
    DOMAIN_CTX
    || b"|"
    || credential_payload_hash
    || b"|"
    || int_to_bytes(threshold, 32)
)
```

where:

- `credential_payload_hash` is SHA‑256(canonical JSON), 32 bytes.
- `int_to_bytes(threshold, 32)` is the big‑endian 32‑byte encoding of the
  integer threshold.

This same `context` is used in:

- `schnorr_prove_opening` / `schnorr_verify_opening`.
- `bulletproof_range_prove` / `bulletproof_range_verify`.

### 3.3 Schnorr opening proof transcript

For the Pedersen commitment opening proof, the challenge scalar `c` is:

```text
c = hash_to_scalar(
    [
      DOMAIN_ZKP,
      G_bytes,
      H_bytes,
      C_bytes,     # commitment V
      R_bytes,     # ephemeral commitment
      context,
    ],
    dst = b"POF_SCHNORR_OPEN_V1",
)
```

where `G_bytes`, `H_bytes`, `C_bytes`, `R_bytes` are compressed point
encodings.

### 3.4 Bulletproofs range‑proof and IPP transcripts

For both `bulletproof_range_prove` and `bulletproof_range_verify`, the
initial Bulletproof range‑proof transcript is:

```text
transcript = [
    DOMAIN_ZKP,
    b"BP_RANGE_V1",
    G_bytes, H_bytes, Q_bytes,
    V_bytes,         # Pedersen commitment to v
    A_bytes, S_bytes,
    context,
]
```

From this transcript:

```text
y = hash_to_scalar(transcript, dst = b"POF_BP_Y_V1")
z = hash_to_scalar(transcript + [int_to_bytes(y, 32)], dst = b"POF_BP_Z_V1")
```

Then, after forming `T1` and `T2`, the transcript is extended:

```text
transcript2 = transcript + [
    T1_bytes, T2_bytes,
    int_to_bytes(y, 32),
    int_to_bytes(z, 32),
]

x = hash_to_scalar(transcript2, dst = b"POF_BP_X_V1")
```

The same sequence and order **MUST** be used in both prover and verifier.

### 3.5 IPP transcript for verification scalars

For the inner‑product argument, the IPP transcript used to derive the
`u_i` challenges is:

```text
ipp_transcript = transcript2 + [int_to_bytes(x, 32)]
```

and then in `ipp_verification_scalars`:

```text
transcript_curr = list(ipp_transcript)
for each (L_i, R_i) in proof.ipp.L, proof.ipp.R:
    transcript_curr.append(L_i_bytes)
    transcript_curr.append(R_i_bytes)
    u_i = hash_to_scalar(transcript_curr, dst = b"POF_BP_IPP_CHAL_V1")
```

Implementations **MUST**:

- Use compressed point encodings for `L_i`, `R_i` in the transcript.
- Append in the exact order `[..., L_i, R_i]` per round.

The derived vectors `u_sq`, `u_inv_sq`, and `s` follow Dalek’s
`InnerProductProof::verification_scalars` semantics (see the reference
implementation for the exact recurrence).

------------------------------------------------------------------------

## 4. Generator derivation and parameter setup

The engine setup for `n_bits` (power of two) generates:

- Base generators:
  - `G` = standard secp256k1 generator.
  - `H` = `G` multiplied by a hash‑derived scalar.
  - `Q` = `G` multiplied by a different hash‑derived scalar.
- Vectors:
  - `G_vec[i]` and `H_vec[i]` derived deterministically via
    `DOMAIN_GEN` and index‑tagging.

Reference logic:

```python
def derive_generator(tag: bytes) -> Point:
    s = hash_to_scalar([tag], dst=DOMAIN_GEN)
    if s == 0:
        s = 1
    return s * G_base

def derive_generators(prefix: bytes, n: int) -> List[Point]:
    return [derive_generator(prefix + b":" + str(i).encode("utf-8")) for i in range(n)]
```

Setup:

```python
G = G_base
H = derive_generator(b"H")
Q = derive_generator(b"Q")

G_vec = derive_generators(b"G_vec", n_bits)
H_vec = derive_generators(b"H_vec", n_bits)
```

The setup parameters exported by `zkp_setup(n_bits)` are:

```json
{
  "curve": "secp256k1",
  "order": <int>,
  "G": <point>,
  "H": <point>,
  "Q": <point>,
  "n_bits": <int>,
  "G_vec": [<point>; n_bits],
  "H_vec": [<point>; n_bits],
  "domain_separator": "POF_ZKP_V1"  // when serialized
}
```

When serialized into JSON, points are represented as compressed hex
strings (`point_bytes.hex()`).

------------------------------------------------------------------------

## 5. Proof package schema and encoding

### 5.1 Internal proof package (engine‑level)

The engine exposes:

```python
proof_package = zkp_prove(params, balance, threshold, credential_payload)
is_valid = zkp_verify(params, threshold, credential_payload, proof_package)
```

At the Python object level, `proof_package` has the shape:

```json
{
  "commitment": "<hex string>",           // compressed V
  "schnorr_opening": {
    "R": "<hex string>",                  // compressed R
    "s_v": <int>,                         // scalar
    "s_r": <int>                          // scalar
  },
  "bulletproof": {
    "A": "<hex string>",
    "S": "<hex string>",
    "T1": "<hex string>",
    "T2": "<hex string>",
    "tau_x": <int>,
    "mu": <int>,
    "t_hat": <int>,
    "ipp": {
      "L": ["<hex string>", ...],
      "R": ["<hex string>", ...],
      "a": <int>,
      "b": <int>
    }
  },
  "meta": {
    "n_bits": <int>,
    "threshold": <int>,
    "credential_payload_hash": "<hex string>",
    "context_hash": "<hex string>",
    "domain_separator": "POF_ZKP_V1"
  }
}
```

All hex strings are lower‑case, obtained via `bytes.hex()`. On verify,
the implementation:

- Checks that `meta["threshold"]` equals the verifier’s `threshold`.
- Recomputes `credential_payload_hash` from the provided
  `credential_payload` and checks equality with `meta`.
- Recomputes `context` from `DOMAIN_CTX`, `credential_payload_hash`, and
  `threshold`.
- Reconstructs `V`, `A`, `S`, `T1`, `T2`, all L/R points, and scalars
  from ints and hex strings.
- Runs:
  - Schnorr opening verifier (`schnorr_verify_opening`).
  - Bulletproof first equation.
  - `bulletproofs_mega_check`.

Any deviation returns `False`.

### 5.2 Credential‑level proof package and tokenization

At the credential/token level (as seen in `prd.md` and
`zkp_simulation.py`), the proof package is embedded in a **token**:

```json
{
  "credential_payload": { "...": "..." },
  "zkp_proof": { "...": "engine proof_package json ..." },
  "token_version": "v1"
}
```

Tokenization is:

```python
raw = json.dumps(proof_package, separators=(",", ":")).encode("utf-8")
token = base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")
```

Decoding:

- Base64url with padding restored (`=`) to a multiple of 4.
- UTF‑8 decode; JSON parse; require a top‑level dict with
  `credential_payload` and `zkp_proof` keys.

Independent implementations **MUST** match this behavior to interoperate
at the token level.

------------------------------------------------------------------------

## 6. Error handling and edge conditions

Implementations **SHOULD** mirror the reference behavior:

- **Setup:**
  - `n_bits` must be a positive power of two; otherwise: error.
- **Prove:**
  - `balance < 0` or `threshold < 0`: error.
  - `balance < threshold`: error
    (`"insufficient funds for chosen tier (balance < threshold)"`).
  - `v = balance - threshold` must satisfy `0 ≤ v < 2^n_bits`; otherwise:
    error (`"value too large for configured n_bits"`).
- **Verify:**
  - Any malformed or inconsistent data (missing fields, invalid hex,
    non‑matching hashes, invalid challenges, etc.) must cause the
    verifier to return `False` (never raise) at the API level.

At the token level (`decode_token` in `zkp_simulation.py`), decoders
return `(empty_dict, "error_reason")` for malformed tokens; callers then
**MUST NOT** attempt ZKP verification.

------------------------------------------------------------------------

## 7. Requirements for independent implementations

An independent implementation that wishes to be byte‑level compatible
with this engine **MUST**:

1. Use secp256k1, SHA‑256, and the exact domain separators and tags
   listed above.
2. Implement canonical JSON and credential payload hashing exactly as in
   §2.
3. Derive generators and vector generators as in §4.
4. Follow the exact transcript construction and challenge derivation
   sequences in §3.
5. Use compressed point encodings and big‑endian 32‑byte scalars for all
   serialized elliptic curve data.
6. Implement range‑proof and IPP logic such that:
   - The Bulletproof statement and first equation match
     `zkp_architecture.md`.
   - The range‑proof → IPP handoff follows
     `P = <l, G_vec> + <r, H'> + t_hat·Q` with `H'` and `t_hat` exactly
     as described there.
   - Verification uses a single **mega check** equivalent to
     `bulletproofs_mega_check`.
7. Serialize `proof_package` and credential tokens exactly as in §5.

If these conditions are satisfied, any proof generated by the reference
Python engine should verify in the independent implementation, and vice
versa.

------------------------------------------------------------------------

## 8. Appendix — concrete test vector

This appendix provides a **normative test vector** generated by the
reference engine. An independent implementation should be able to:

1. Recompute the same `credential_payload_hash` and `context_hash`.
2. Verify the proof package successfully.
3. Generate a byte‑for‑byte identical token string given the same inputs.

### 8.1 Inputs

- `n_bits = 32`
- `balance = 350000`
- `threshold = 250000`
- `tier_id = "TIER_250K"`
- `member_pseudonym = "member-xyz"`
- `issued_at = "2026-03-04T07:57:01Z"`
- `integrity = {"status": "OK", "platform": "iOS", "risk_flags": [], "attested_at": "2026-03-04T07:57:01Z"}`
- `credential_id = "b043671b-94b2-48fb-afd3-730b2531ea1b"`

### 8.2 Canonical credential payload JSON

The canonical JSON (as produced by the reference implementation) is:

```json
{"credential_id":"b043671b-94b2-48fb-afd3-730b2531ea1b","integrity":{"attested_at":"2026-03-04T07:57:01Z","platform":"iOS","risk_flags":[],"status":"OK"},"issued_at":"2026-03-04T07:57:01Z","member_pseudonym":"member-xyz","tier_id":"TIER_250K"}
```

### 8.3 Engine‑level proof_package JSON

The engine returns the following `proof_package` (shown here as canonical
JSON with sorted keys and compact separators):

```json
{"bulletproof":{"A":"02ab8edfa336b794aea4ee9d4b61efa70cff65e5c2824fa07f92671beca6d04c8c","S":"0247a0877643b53cde6b41b21503a622dccd85ced2f27b1b4f81f14554ea369aab","T1":"038e9a7edcf5d4de2738d6ce89b93645263d36338fd74124c2958de41d25fbf31c","T2":"033f9672cdcb4a062b339060db27dfd80ad17de99f6f1447d676a379d18247ecf4","ipp":{"L":["024d58bd90efb298a2890f2eb128e71425c8f7940c284ab06b7c72041b5c4c832a","0360af51ea9c46629220c5ca7ea9f9feaa896c706634bf6f6ac7e4a0e1d02eca6a","020998476c433536b15b44511bf4a3f005367bfbba5d542d5ff8c2bfc3d02d85bd","02ebf66e182af25a596d73484b7520187f73b6f3156c25dffe11269f055aa55dc1","02b9ee27630e5a77dca27f9f94c55cd974c88484269c0d48ec1861eea76e3abfed"],"R":["0232b9f86e4c27fd73ef1abc45c18b686e626822d15ff80285e6ee8a03209435bd","02a434458e5119f42c167bfb9660c625b2b20a42e886c93e3a6d1e938d78fe4524","0307277fd997f4b7caa91399add76bca6eaac632f16a7df6b47b766095f3961603","035a0f356b1761c1aa31bb34b37c3c24e404b110968a2e8d291b8ae7a110b37ce3","03942c2237894ac5e4e479113c60da17abd4e77e1264cbc9fecb54ef2d232b1b54"],"a":15535758677767483560939081416202178013972905867545577139580050230983755081299,"b":46985036262198908266250243082071560232359734781857901908371448585410675488390},"mu":17729985644864087207043758870845053443174220318862328391030826813853368883278,"t_hat":6474106402716879099508112986767097682833910598443468199399354513320154412572,"tau_x":64472904486602385056939232785253205452751107443184432797437503413049671180511},"commitment":"02bb65deeda0957db6aaa297c435eb469e41639fdf3c5321f2635107488b62fac2","meta":{"context_hash":"be53118cf71811a1f13e98a5ba4b06db37655e982d254896f544d17d0c5dcc66","credential_payload_hash":"08d4ddbec35e98473605b1bf3feec39436db59a970822e2c31a9e2e644fe131f","domain_separator":"POF_ZKP_V1","n_bits":32,"threshold":250000},"schnorr_opening":{"R":"038b5bc26651542bfb96485b03061e0d45cf5f79c460cf31d2b6ee4c9ff9f65fe6","s_r":27896761329402896910579991612324300093452215682864905981393635295748616621737,"s_v":37281988915509488133242948278840345723062973572310567011003231156876479736595}}
```

### 8.4 Credential‑level token

Wrapping the credential payload and `proof_package` into:

```json
{
  "credential_payload": { ... as in §8.2 ... },
  "zkp_proof": { ... as in §8.3 ... },
  "token_version": "v1"
}
```

and encoding via the base64url JSON scheme described in §5.2 yields the
opaque token:

```text
eyJjcmVkZW50aWFsX3BheWxvYWQiOnsiY3JlZGVudGlhbF9pZCI6ImIwNDM2NzFiLTk0YjItNDhmYi1hZmQzLTczMGIyNTMxZWExYiIsIm1lbWJlcl9wc2V1ZG9ueW0iOiJtZW1iZXIteHl6IiwidGllcl9pZCI6IlRJRVJfMjUwSyIsImlzc3VlZF9hdCI6IjIwMjYtMDMtMDRUMDc6NTc6MDFaIiwiaW50ZWdyaXR5Ijp7InN0YXR1cyI6Ik9LIiwicGxhdGZvcm0iOiJpT1MiLCJyaXNrX2ZsYWdzIjpbXSwiYXR0ZXN0ZWRfYXQiOiIyMDI2LTAzLTA0VDA3OjU3OjAxWiJ9fSwiemtwX3Byb29mIjp7ImNvbW1pdG1lbnQiOiIwMmJiNjVkZWVkYTA5NTdkYjZhYWEyOTdjNDM1ZWI0NjllNDE2MzlmZGYzYzUzMjFmMjYzNTEwNzQ4OGI2MmZhYzIiLCJzY2hub3JyX29wZW5pbmciOnsiUiI6IjAzOGI1YmMyNjY1MTU0MmJmYjk2NDg1YjAzMDYxZTBkNDVjZjVmNzljNDYwY2YzMWQyYjZlZTRjOWZmOWY2NWZlNiIsInNfdiI6MzcyODE5ODg5MTU1MDk0ODgxMzMyNDI5NDgyNzg4NDAzNDU3MjMwNjI5NzM1NzIzMTA1NjcwMTEwMDMyMzExNTY4NzY0Nzk3MzY1OTUsInNfciI6Mjc4OTY3NjEzMjk0MDI4OTY5MTA1Nzk5OTE2MTIzMjQzMDAwOTM0NTIyMTU2ODI4NjQ5MDU5ODEzOTM2MzUyOTU3NDg2MTY2MjE3Mzd9LCJidWxsZXRwcm9vZiI6eyJBIjoiMDJhYjhlZGZhMzM2Yjc5NGFlYTRlZTlkNGI2MWVmYTcwY2ZmNjVlNWMyODI0ZmEwN2Y5MjY3MWJlY2E2ZDA0YzhjIiwiUyI6IjAyNDdhMDg3NzY0M2I1M2NkZTZiNDFiMjE1MDNhNjIyZGNjZDg1Y2VkMmYyN2IxYjRmODFmMTQ1NTRlYTM2OWFhYiIsIlQxIjoiMDM4ZTlhN2VkY2Y1ZDRkZTI3MzhkNmNlODliOTM2NDUyNjNkMzYzMzhmZDc0MTI0YzI5NThkZTQxZDI1ZmJmMzFjIiwiVDIiOiIwMzNmOTY3MmNkY2I0YTA2MmIzMzkwNjBkYjI3ZGZkODBhZDE3ZGU5OWY2ZjE0NDdkNjc2YTM3OWQxODI0N2VjZjQiLCJ0YXVfeCI6NjQ0NzI5MDQ0ODY2MDIzODUwNTY5MzkyMzI3ODUyNTMyMDU0NTI3NTExMDc0NDMxODQ0MzI3OTc0Mzc1MDM0MTMwNDk2NzExODA1MTEsIm11IjoxNzcyOTk4NTY0NDg2NDA4NzIwNzA0Mzc1ODg3MDg0NTA1MzQ0MzE3NDIyMDMxODg2MjMyODM5MTAzMDgyNjgxMzg1MzM2ODg4MzI3OCwidF9oYXQiOjY0NzQxMDY0MDI3MTY4NzkwOTk1MDgxMTI5ODY3NjcwOTc2ODI4MzM5MTA1OTg0NDM0NjgxOTkzOTkzNTQ1MTMzMjAxNTQ0MTI1NzIsImlwcCI6eyJMIjpbIjAyNGQ1OGJkOTBlZmIyOThhMjg5MGYyZWIxMjhlNzE0MjVjOGY3OTQwYzI4NGFiMDZiN2M3MjA0MWI1YzRjODMyYSIsIjAzNjBhZjUxZWE5YzQ2NjI5MjIwYzVjYTdlYTlmOWZlYWE4OTZjNzA2NjM0YmY2ZjZhYzdlNGEwZTFkMDJlY2E2YSIsIjAyMDk5ODQ3NmM0MzM1MzZiMTViNDQ1MTFiZjRhM2YwMDUzNjdiZmJiYTVkNTQyZDVmZjhjMmJmYzNkMDJkODViZCIsIjAyZWJmNjZlMTgyYWYyNWE1OTZkNzM0ODRiNzUyMDE4N2Y3M2I2ZjMxNTZjMjVkZmZlMTEyNjlmMDU1YWE1NWRjMSIsIjAyYjllZTI3NjMwZTVhNzdkY2EyN2Y5Zjk0YzU1Y2Q5NzRjODg0ODQyNjljMGQ0OGVjMTg2MWVlYTc2ZTNhYmZlZCJdLCJSIjpbIjAyMzJiOWY4NmU0YzI3ZmQ3M2VmMWFiYzQ1YzE4YjY4NmU2MjY4MjJkMTVmZjgwMjg1ZTZlZThhMDMyMDk0MzViZCIsIjAyYTQzNDQ1OGU1MTE5ZjQyYzE2N2JmYjk2NjBjNjI1YjJiMjBhNDJlODg2YzkzZTNhNmQxZTkzOGQ3OGZlNDUyNCIsIjAzMDcyNzdmZDk5N2Y0YjdjYWE5MTM5OWFkZDc2YmNhNmVhYWM2MzJmMTZhN2RmNmI0N2I3NjYwOTVmMzk2MTYwMyIsIjAzNWEwZjM1NmIxNzYxYzFhYTMxYmIzNGIzN2MzYzI0ZTQwNGIxMTA5NjhhMmU4ZDI5MWI4YWU3YTExMGIzN2NlMyIsIjAzOTQyYzIyMzc4OTRhYzVlNGU0NzkxMTNjNjBkYTE3YWJkNGU3N2UxMjY0Y2JjOWZlY2I1NGVmMmQyMzJiMWI1NCJdLCJhIjoxNTUzNTc1ODY3Nzc2NzQ4MzU2MDkzOTA4MTQxNjIwMjE3ODAxMzk3MjkwNTg2NzU0NTU3NzEzOTU4MDA1MDIzMDk4Mzc1NTA4MTI5OSwiYiI6NDY5ODUwMzYyNjIxOTg5MDgyNjYyNTAyNDMwODIwNzE1NjAyMzIzNTk3MzQ3ODE4NTc5MDE5MDgzNzE0NDg1ODU0MTA2NzU0ODgzOTB9fSwibWV0YSI6eyJuX2JpdHMiOjMyLCJ0aHJlc2hvbGQiOjI1MDAwMCwiY3JlZGVudGlhbF9wYXlsb2FkX2hhc2giOiIwOGQ0ZGRiZWMzNWU5ODQ3MzYwNWIxYmYzZmVlYzM5NDM2ZGI1OWE5NzA4MjJlMmMzMWE5ZTJlNjQ0ZmUxMzFmIiwiY29udGV4dF9oYXNoIjoiYmU1MzExOGNmNzE4MTFhMWYxM2U5OGE1YmE0YjA2ZGIzNzY1NWU5ODJkMjU0ODk2ZjU0NGQxN2QwYzVkY2M2NiIsImRvbWFpbl9zZXBhcmF0b3IiOiJQT0ZfWktQX1YxIn19LCJ0b2tlbl92ZXJzaW9uIjoidjEifQ
```

