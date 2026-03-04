## ZKP Conformance & Diagnostics – Command Cheatsheet

All commands assume you are in the **project root**:

```bash
cd c:\Users\RobertTomasJohnston\OneDrive\Documents\Coding\Projects\privateclub_zkp
```

Use PowerShell syntax if preferred; the module paths are the same.

------------------------------------------------------------------------

## 1. High-level simulation

- **Run full end-to-end ZKP simulation**

  ```bash
  python -m src.zkp.zkp_simulation
  ```

  Runs the product-level simulation: member side generates a credential +
  proof, verifier side verifies it, and multiple scenarios (PASS/FAIL,
  integrity, old timestamp, corrupted token) are exercised per `prd.md`.

------------------------------------------------------------------------

## 2. Internal ZKP tests (IPP core + Bulletproof mega-check)

- **Run all internal ZKP diagnostics (IPP core + mega-check)**

  ```bash
  python -m src.zkp.run_internal_tests
  ```

  Convenience wrapper that runs `debug_ipp_core` (IPP core self-test) and
  `test_step3_mega_check` (Bulletproofs mega-check validation) in
  sequence and prints a short summary.

------------------------------------------------------------------------

## 3. Diagnostics: inner-product proof (IPP)

- **IPP core self-test (no Bulletproofs)**

  ```bash
  python -m src.zkp.diagnostics.debug_ipp_core
  ```

  Exercises `_ipp_prove` and `_ipp_verify` directly on small random
  inner-product instances (n=2) to confirm algebraic consistency and the
  Dalek-style `ipp_verification_scalars` aggregation.

- **Single-round IPP debug for Bulletproof range proof**

  ```bash
  python -m src.zkp.diagnostics.debug_ipp_round
  ```

  Builds a full Bulletproof range proof with `n_bits = 2`, reconstructs
  the `InnerProductProof` object, and runs `bulletproof_range_verify`
  once, printing whether verification succeeded; useful for step-by-step
  IPP debugging.

- **Step 3 mega-check validation (corruption tests)**

  ```bash
  python -m src.zkp.diagnostics.test_step3_mega_check
  ```

  Verifies that a valid Bulletproof range proof (n_bits=2) passes the
  first equation + mega-check and that targeted corruptions of `L[0]`,
  `R[0]`, `a`, `b`, or the generator set are all rejected.

------------------------------------------------------------------------

## 4. Conformance / interoperability tests

- **Run the ZKP conformance suite for the Python engine**

  ```bash
  python -m src.zkp.conformance_suite
  ```

  Validation and benchmark harness that:

  - Verifies the engine accepts the **canonical token** from
    `zkp_prd.md` (normative test vector).
  - Runs basic self-cross tests (same engine as prover and verifier) to
    ensure a valid proof verifies and insufficient funds cannot be
    proved.

  Intended as the primary check that alternative implementations
  following `zkp_prd.md` interoperate with the reference engine.

------------------------------------------------------------------------

## 5. Optional: IPP debug logging

For deeper debugging of the IPP recursion on n=2 cases, enable the
environment flag before running any of the diagnostics that hit
`_ipp_prove` / `_ipp_verify`:

```powershell
$env:POF_IPP_DEBUG = "1"
python -m src.zkp.diagnostics.debug_ipp_round  2> ipp_debug.log
```

This causes `_ipp_prove` and `_ipp_verify` to emit detailed step data to
stderr (L/R points, challenges, final G/H, etc.) which you can redirect
to a log file for inspection.

