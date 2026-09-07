# Changelog

All notable changes to **Agnara Historical Reference Application #007 (`agnara-policy-guardrails`)** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.1.0] - 2026-09-06

### Added
- Canonical implementation of **Agnara Historical Reference Application #007 (`agnara-policy-guardrails`)**.
- Domain models and in-memory ledger in `domain.py`:
  - `Account`, `UserProfile`, `Subscription`, `PaymentReceipt` dataclasses.
  - `SubscriptionStatus` enumeration.
  - `FinancialLedger` thread-safe repository (PEP 703 compatible) with deterministic seeding.
- Guardrails and execution policies in `guardrails.py`:
  - `DailySpendingLimitPolicy` (conforming to `agnara.Policy` protocol, payload-aware threshold checking).
  - `SubscriptionActiveGuardrailPolicy` (business validation before destructive revocation).
  - `FinancialConfirmationVerifier` (implementing `agnara.ConfirmationVerifier` protocol, binding tokens to capability, principal, and invocation).
  - `register_guarded_capability()` registration helper binding declarative metadata with runtime `Policy` objects via `CapabilityDefinition.declare()`.
  - Four reference capabilities:
    - `finance.view_balance`: `Risk.LOW`, effects=`["read"]`, `idempotent=True`, `confirmation=NEVER`, `ScopePolicy(["accounts:read"])`.
    - `finance.update_profile`: `Risk.MEDIUM`, effects=`["database-write"]`, `idempotent=True`, `confirmation=NEVER`, `ScopePolicy(["profile:write"])`.
    - `finance.cancel_subscription`: `Risk.HIGH`, effects=`["database-write", "destructive"]`, `idempotent=True`, `confirmation=NEVER`, `ScopePolicy(["subscriptions:write"])`, `SubscriptionActiveGuardrailPolicy`.
    - `finance.send_payment`: `Risk.CRITICAL`, effects=`["financial-write"]`, `idempotent=False`, `confirmation=REQUIRED`, `ScopePolicy(["payments:transfer"])`, `DailySpendingLimitPolicy`, `ConfirmationPolicy`.
- Interactive CLI demonstration in `app.py` covering 6 educational phases:
  1. Agent discovery & machine-readable capability introspection via `describe_app()`.
  2. Read-only low-risk polling with scope authorization.
  3. Idempotent state mutation and retry safety.
  4. High-risk destructive actions with custom domain guardrails.
  5. Critical non-idempotent financial writes with two-phase confirmation tokens.
  6. Framework guarantees vs application responsibility boundaries.
- Comprehensive test suite in `tests/`:
  - `test_metadata_inspection.py` (registry effects filtering, schema generation, dependency protection).
  - `test_scope_guardrails.py` (anonymous caller denial, principal scope evaluation).
  - `test_confirmation_flow.py` (missing verifier compilation check, missing evidence interaction demand, invalid evidence rejection, valid evidence approval).
  - `test_custom_policies.py` (spending limits, scope override bypass, cancellation reason validation).
  - `test_idempotency_semantics.py` (read effect purity, idempotent retry safety, non-idempotent side-effect duplication).
- Architectural documentation in `ARCHITECTURE.md`.
- AI agent operational guide in `AGENTS.md`.
- Repository pinned to `agnara==0.1.0a3` and CPython >= 3.14.
- Repository status marked as **Historical / Frozen**.
