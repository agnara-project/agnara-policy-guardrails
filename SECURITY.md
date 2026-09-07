# Security Policy

## Supported Versions

This repository is **Agnara Historical Reference Application #007** and is permanently pinned to **`agnara==0.1.0a3`**.

| Package | Version | Supported |
|---|---|---|
| `agnara` | `0.1.0a3` | Historical Reference (Security patches only if severe) |
| `agnara-policy-guardrails` | `0.1.0` | Frozen / Archived |

---

## 1. Security Architecture & Threat Model

This reference application demonstrates defensive security boundaries for autonomous systems:
- **Principle of Least Privilege:** Callers must hold explicit scopes validated by `ScopePolicy`.
- **Pre-execution Verification:** Policies halt execution before touching backend domain state or calling external handlers.
- **Fail-Closed Confirmation:** If confirmation evidence is absent, expired, or invalid, execution is rejected with `FailureCode.FORBIDDEN` or `FailureCode.INTERACTION_REQUIRED`.
- **Protected Parameters:** DI-injected services (such as `FinancialLedger`) and `ExecutionContext` are classified as protected parameters and cannot be overridden by untrusted caller payload parameters.

---

## 2. Reporting a Vulnerability

If you discover a potential security vulnerability in Agnara core or in this reference application:

1. **Do NOT open a public GitHub issue.**
2. Send a detailed advisory to the Agnara security team at `security@agnara.dev`.
3. Please include:
   - Reproduction steps or proof-of-concept script.
   - Affected capability or policy evaluation phase.
   - Potential impact on input validation or authorization boundaries.

We will acknowledge receipt within 48 hours and coordinate responsible disclosure.
