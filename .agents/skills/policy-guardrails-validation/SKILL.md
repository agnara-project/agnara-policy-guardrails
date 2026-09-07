---
name: policy-guardrails-validation
description: Operational workflow for verifying policy metadata, execution guardrails, confirmation verifiers, and application boundaries against agnara==0.1.0a3.
---

# Policy Guardrails Validation Skill

Use this skill when auditing, verifying, or testing capability metadata, execution policies, confirmation flows, and framework boundaries in **Agnara Historical Reference Application #007 (`agnara-policy-guardrails`)**.

---

## 1. When to Use This Skill

Activate this skill whenever:
- Verifying the distinction between declarative metadata (`effects`, `risk`, `idempotency`) and runtime enforcement in `agnara==0.1.0a3`.
- Auditing how `ExecutionPlan.compile` inspects declarations and enforces confirmation verifiers when `Confirmation.REQUIRED`.
- Checking that `ScopePolicy` correctly validates `context.principal.scopes` against required labels and returns `PolicyFailure` on missing scopes.
- Verifying the two-phase confirmation protocol: probe without evidence -> `INTERACTION_REQUIRED`, invalid token -> `FORBIDDEN`, valid token -> execution.
- Verifying that application-level policies conforming to `agnara.Policy` evaluate before input validation and handler execution.
- Checking that `describe_app` and `CapabilityDescriptor` export truthful machine-readable schemas for pre-invocation inspection.

---

## 2. Relevant Inputs

- **`CapabilityDefinition`:** The immutable capability declaration containing `scopes`, `effects`, `risk`, `confirmation`, `idempotency`, and `policies`.
- **`ScopePolicy`:** Agnara's built-in transport-neutral scope authorization policy.
- **`ConfirmationPolicy` & `ConfirmationVerifier`:** The interaction enforcement engine and application verification protocol.
- **`ExecutionContext` & `Principal`:** The runtime environment carrying identity, scopes, and confirmation evidence.
- **`describe_app`:** The introspection builder providing pre-execution contract visibility.

---

## 3. Ordered Implementation Workflow

### Step 1: Baseline & Dependency Check
1. Ensure the Python environment runs CPython >= 3.14.
2. Confirm the installed framework is strictly `agnara==0.1.0a3`:
   ```python
   import agnara

   assert agnara.__version__ == "0.1.0a3"
   ```

### Step 2: Metadata vs Enforcement Audit
1. Verify that `effects` are declarative only (core runtime does not enforce read-only DB isolation).
2. Verify that `risk` is an inspectable categorization (core does not automatically halt high-risk calls without policies).
3. Verify that `idempotency` is an inspection contract for clients (core does not deduplicate requests).
4. Verify that `@app.capability(scopes={...})` is declarative metadata unless accompanied by `ScopePolicy`.

### Step 3: Scope Enforcement Verification
1. Test anonymous invocation against scoped capabilities to verify rejection with `FailureCode.FORBIDDEN` and descriptive missing scope messages.
2. Test authorized principals with exact scopes to verify successful passage.

### Step 4: Confirmation Lifecycle Verification
1. Verify that compiling an `ExecutionPlan` with `confirmation=Confirmation.REQUIRED` without a verifier raises `DefinitionError`.
2. Verify that invocation without evidence yields `FailureCode.INTERACTION_REQUIRED` containing `InteractionRequest` details.
3. Verify that invocation with rejected evidence yields `FailureCode.FORBIDDEN`.
4. Verify that valid evidence authorizes execution.

### Step 5: Application Policy Boundary Verification
1. Verify that custom domain guardrails (`DailySpendingLimitPolicy`, `SubscriptionActiveGuardrailPolicy`) implement `agnara.Policy`.
2. Confirm that domain guardrail logic is clearly identified as application-level and never attributed to core Agnara.

---

## 4. Operational Boundaries & Negative Constraints

- **Never describe Agnara metadata as an enforced security guarantee unless the public a3 runtime demonstrably enforces it.**
- **Never turn application-level policy logic into a claimed Agnara framework capability.**
- **Do not modernize this repository using later Agnara policy, authorization, risk, confirmation, or execution APIs.**
- **Do NOT introduce third-party security, auth, or policy engines (OAuth, IAM, OPA).**

---

## 5. Validations & Definition of Done

The policy guardrails validation workflow is complete when:
- [ ] `pytest -v` runs all tests with zero failures.
- [ ] `python app.py` completes all 6 educational phases with exit code `0`.
- [ ] `ruff check .` and `ruff format --check .` exit with code `0`.
- [ ] The Policy Support Matrix in `README.md` and `ARCHITECTURE.md` matches executable evidence.
