---
name: documentation
description: Standards and synchronization rules for maintaining Agnara policy guardrails documentation.
---

# Documentation Skill

Use this skill when reading, authoring, or updating documentation in **Agnara Historical Reference Application #007 (`agnara-policy-guardrails`)**.

---

## 1. When to Use This Skill

Activate this skill whenever:
- Updating or auditing `README.md`, `ARCHITECTURE.md`, or `AGENTS.md`.
- Documenting the distinction between declarative metadata (`effects`, `risk`, `idempotency`, `scopes`) and runtime enforcement.
- Maintaining the Policy Support Matrix comparing declared properties vs Agnara runtime behavior vs application responsibilities.
- Recording historical release notes in `CHANGELOG.md`.

---

## 2. Relevant Inputs

- **`README.md`:** Human-oriented pedagogical guide and reference manual.
- **`AGENTS.md`:** Machine-oriented operational contract for AI coding agents.
- **`ARCHITECTURE.md`:** Architectural deep dive into the guardrails pipeline, ADR alignments, and framework boundaries.
- **`CHANGELOG.md`:** Versioned release history under Keep a Changelog.

---

## 3. Ordered Implementation Workflow

### Step 1: Conceptual Separation Audit
Ensure all documentation strictly separates:
1. **Agnara capability declaration:** Metadata recorded on `CapabilityDefinition`.
2. **Agnara introspection:** Metadata inspected via `describe_app()` and `CapabilityDescriptor`.
3. **Agnara runtime enforcement:** Real decisions made by `_execute` and built-in policies (`ScopePolicy`, `ConfirmationPolicy`).
4. **Application-level policy:** Local decision functions (`DailySpendingLimitPolicy`, `SubscriptionActiveGuardrailPolicy`).

### Step 2: Historical Baseline Protection
1. Verify that `agnara==0.1.0a3` and CPython >= 3.14 are prominently cited.
2. Ensure the Historical / Frozen status is visibly displayed.
3. Confirm that no speculative or post-a3 APIs are described as existing in `0.1.0a3`.

### Step 3: Support Matrix Maintenance
Maintain an accurate support matrix reflecting actual verified behavior:
- `scopes`: Declarative metadata; enforced only when `ScopePolicy` is attached.
- `effects`: Declarative metadata; not verified against code by core runtime.
- `risk`: Declarative metadata; does not halt execution without explicit policy.
- `idempotency`: Declarative tri-state; no automatic caching or deduplication in runtime.
- `confirmation`: Validated by `ExecutionPlan.compile` when `REQUIRED`; halts execution with `INTERACTION_REQUIRED` if evidence missing.

---

## 4. Operational Boundaries & Negative Constraints

- **No Speculative Claims:** Never describe features from later Agnara versions as present in `0.1.0a3`.
- **No Attributing Application Logic to Agnara:** Never call example guardrails "Agnara Policy Engine".
- **No Placeholder Text:** Never leave `TODO`, `TBD`, or temporary notes in public documentation.

---

## 5. Validations & Definition of Done

The documentation workflow is complete when:
- [ ] `README.md`, `ARCHITECTURE.md`, and `AGENTS.md` are aligned with the historical baseline.
- [ ] The Policy Support Matrix matches the passing test suite results.
- [ ] Markdown files pass formatting checks with `ruff format --check .`.
