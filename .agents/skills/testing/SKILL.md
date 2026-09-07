---
name: testing
description: Testing standards, quality gates, and negative evidence verification for Agnara policy guardrails.
---

# Testing Skill

Use this skill when authoring, modifying, or executing tests in **Agnara Historical Reference Application #007 (`agnara-policy-guardrails`)**.

---

## 1. When to Use This Skill

Activate this skill whenever:
- Adding or modifying unit tests in `tests/`.
- Verifying metadata introspection, scope enforcement, or confirmation lifecycle.
- Testing domain custom policies and application-level guardrails.
- Adding negative evidence tests verifying compile-time and runtime rejections.
- Running the complete test suite or linting quality gates.

---

## 2. Relevant Inputs

- **`tests/test_agnara_metadata_and_introspection.py`:** Tests for `describe_app`, `CapabilityDescriptor`, and effect queries.
- **`tests/test_agnara_scope_policy.py`:** Tests for Agnara's built-in `ScopePolicy` and `Principal`.
- **`tests/test_agnara_confirmation_enforcement.py`:** Tests for built-in confirmation compilation check and interaction demand.
- **`tests/test_application_guardrails.py`:** Tests for application-level spending limit and cancellation policies.
- **`tests/test_idempotency_and_effects_semantics.py`:** Tests for behavioral side effects and non-idempotent duplicate calls.

---

## 3. Ordered Implementation Workflow

### Step 1: Self-Contained Test Design
1. Do not require external async plugins (such as `pytest-asyncio`).
2. Write synchronous test functions using `asyncio.run(_run())` for async execution.
3. Keep test functions self-contained, readable, and focused on single guardrail assertions.
4. Clearly separate Agnara framework behavior tests from example application policy tests.

### Step 2: Positive & Negative Assertions
1. Test the happy path (authorized, confirmed calls produce `Success[T]`).
2. Test the rejection path:
   - Scope failure produces `Failure(FailureCode.FORBIDDEN, message="missing required scopes: ...")`.
   - Missing confirmation produces `Failure(FailureCode.INTERACTION_REQUIRED, message=..., details=...)`.
   - Spending limit failure produces `Failure(FailureCode.FORBIDDEN, message=...)`.
3. Test negative compile-time evidence:
   - Compiling `Confirmation.REQUIRED` without a verifier raises `DefinitionError`.

### Step 3: Test Execution & Gate Verification
1. Run the test suite:
   ```powershell
   pytest -v
   ```
2. Verify code quality and formatting:
   ```powershell
   ruff check .
   ruff format --check .
   ```

---

## 4. Operational Boundaries & Negative Constraints

- **Do NOT introduce unnecessary test dependencies:** Rely on standard `pytest` and `asyncio.run()`.
- **Do NOT mock Agnara core:** Tests must execute real `ExecutionPlan`, `ScopePolicy`, `ConfirmationPolicy`, and `invoke_result()` mechanics.
- **Do NOT write speculative tests:** Never test for features that exist only in later Agnara releases.

---

## 5. Validations & Definition of Done

The testing workflow is complete when:
- [ ] All tests execute cleanly and pass in `pytest -v`.
- [ ] Tests verify both positive support and negative compile-time/runtime rejections.
- [ ] Agnara framework behavior and application policy behavior are distinctly organized and tested.
- [ ] No warnings are emitted during test collection or execution.
