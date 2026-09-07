# Architecture: `agnara-policy-guardrails`

This document details the architectural principles, component relationships, and execution lifecycle of **Agnara Historical Reference Application #007 (`agnara-policy-guardrails`)** under **`agnara==0.1.0a3`** and **CPython >= 3.14**.

---

## 1. Architectural Mission

The goal of this reference application is to demonstrate how to build an **Agent-Safe API**:
an application surface where operations provide standardized, machine-readable metadata regarding their side effects, operational risk, idempotency, and authorization rules, evaluated by a strict policy engine prior to handler execution.

Traditional API frameworks (e.g. FastAPI, Flask, Django) mix authorization, validation, transport protocols, and business logic into monolithic route decorators or middleware stacks. In contrast, Agnara adheres to:
- **Capability-First Design (ADR 0001):** The capability is the fundamental atomic unit of business logic.
- **Transport Neutrality:** Capabilities know nothing about HTTP, JSON-RPC, MCP, or CLI. Policies evaluate protocol-neutral context objects.
- **Standard Library Purity (ADR 0004):** Zero external modeling or schema dependencies. Core Agnara depends only on Python standard libraries.
- **Two-Phase Compilation (ADR 0005):** Registration occurs at startup, followed by freezing into immutable structures safe for free-threaded execution (PEP 703).
- **Metadata Is Not Authorization (ADR 0008):** Declaring a scope or risk tag on a capability does not grant or deny anything by itself; enforcement requires explicit `Policy` implementations.

---

## 2. The Policy & Guardrail Execution Pipeline

When a caller invokes a capability through `invoke()` or `invoke_result()`, the runtime executes a deterministic, multi-stage guardrail pipeline:

```
                  Caller / Agent Invocation
                              │
                              ▼
                   ExecutionContext Creation
       (Invocation payload, Principal, DIContainer, ConfirmationEvidence)
                              │
                              ▼
            ┌───────────────────────────────────┐
            │ Stage 1: Security & Scopes Policy │
            │      (ScopePolicy.evaluate)       │
            └─────────────────┬─────────────────┘
                              │
                   Passed? ───┴───> No  ──> PolicyDeniedError (FailureCode.FORBIDDEN)
                              │ Yes
                              ▼
            ┌───────────────────────────────────┐
            │  Stage 2: Custom Business Policies│
            │ (DailySpendingLimitPolicy, etc.)  │
            └─────────────────┬─────────────────┘
                              │
                   Passed? ───┴───> No  ──> PolicyDeniedError (FailureCode.FORBIDDEN)
                              │ Yes
                              ▼
            ┌───────────────────────────────────┐
            │   Stage 3: Confirmation Policy    │
            │   (ConfirmationPolicy.evaluate)   │
            └─────────────────┬─────────────────┘
                              │
               Has Evidence? ─┴───> No  ──> InteractionRequiredError
                              │ Yes         (FailureCode.INTERACTION_REQUIRED)
                              ▼
              ConfirmationVerifier.verify()
                              │
               Valid Token? ──┴───> No  ──> PolicyDeniedError (FailureCode.FORBIDDEN)
                              │ Yes
                              ▼
            ┌───────────────────────────────────┐
            │    Stage 4: Input Validation      │
            │   (Strict TypeSchema Checking)    │
            └─────────────────┬─────────────────┘
                              │
                   Valid? ────┴───> No  ──> ValidationError (FailureCode.INVALID_INPUT)
                              │ Yes
                              ▼
            ┌───────────────────────────────────┐
            │    Stage 5: Handler Execution     │
            │ (Dependency injection & Business) │
            └─────────────────┬─────────────────┘
                              │
                              ▼
                       Canonical Outcome
                   Success[T] or Failure[E]
```

### 2.1 Early Abort Semantics
Notice the order of evaluation:
1. Policies evaluate sequentially. If a caller lacks required scopes (`ScopePolicy`), execution aborts immediately before any database or domain state is queried.
2. If spending limit policies fail, execution aborts before confirmation tokens are processed.
3. If confirmation evidence is absent, execution aborts with `FailureCode.INTERACTION_REQUIRED` before input validation or dependency resolution runs.
4. Input validation and dependency injection only execute once all policies yield `PolicySuccess`.

---

## 3. Metadata Axes in Agnara 0.1.0a3

Agnara defines five core metadata properties on `CapabilityDefinition`:

### 3.1 `effects` (`StandardEffect`)
- **Members:** `none`, `read`, `cache-write`, `database-write`, `external-write`, `financial-write`, `destructive`.
- **Purpose:** Declares the operational impact on application state.
- **Inspection:** Callers and agents can filter available capabilities using `FrozenCapabilityRegistry.with_effect(...)`.
- **Guarantee:** Purely declarative in `0.1.0a3`. Core does not wrap handlers in database rollback transactions; the developer is responsible for honest effect declaration.

### 3.2 `risk` (`Risk`)
- **Members:** `low`, `medium`, `high`, `critical`.
- **Purpose:** Categorizes operational consequence.
- **Guarantee:** Purely declarative in `0.1.0a3`. Core does not automatically halt high-risk calls. It allows UI layers and agent orchestrators to display warnings or apply human-in-the-loop gates.

### 3.3 `idempotency` (`Idempotency`)
- **Members:** `yes`, `no`, `unknown`.
- **Default:** `unknown` (per RFC 0001: omission means unknown, never an assumed yes).
- **Purpose:** Declares whether re-executing with identical arguments alters state beyond the initial call.
- **Guarantee:** Core does not implement an automatic idempotency deduplication cache. Callers (e.g. MCP clients or HTTP gateways) must check `idempotency == 'yes'` before issuing automatic retries.

### 3.4 `confirmation` (`Confirmation`)
- **Members:** `never`, `policy`, `required`.
- **Guarantee:** When `Confirmation.REQUIRED`, `ExecutionPlan.compile` enforces that a `ConfirmationVerifier` is passed, and automatically injects a `ConfirmationPolicy` into `plan.policies`.

### 3.5 `scopes` (`frozenset[str]`)
- **Purpose:** Machine-readable permission labels.
- **Guarantee:** Declarative on `CapabilityDefinition`. Evaluated at runtime when paired with `ScopePolicy`.

---

## 4. The Policy Protocol (`agnara.Policy`)

In Agnara 0.1.0a3, policies implement the runtime protocol:

```python
@runtime_checkable
class Policy(Protocol):
    async def evaluate(self, context: ExecutionContext) -> PolicyResult: ...
```

A policy must never raise exceptions to report business denials. It returns one of three immutable outcomes:
1. `PolicySuccess()`: The rule passed; proceed to next policy.
2. `PolicyFailure(reason: str)`: Denied with a caller-safe reason. The runtime converts this into `PolicyDeniedError` / `FailureCode.FORBIDDEN`.
3. `PolicyInteractionRequired(request: InteractionRequest)`: Execution cannot proceed without external caller input (such as confirmation). Converted into `InteractionRequiredError` / `FailureCode.INTERACTION_REQUIRED`.

---

## 5. Confirmation Lifecycle

Agnara models interactive human/agent confirmation as a protocol-neutral, two-phase interaction:

1. **First Invocation (Probe / Unconfirmed):**
   - The caller invokes the capability without `confirmation_evidence`.
   - `ConfirmationPolicy` observes `context.confirmation_evidence is None`.
   - Returns `PolicyInteractionRequired`, halting execution.
   - `invoke_result()` returns:
     ```python
     Failure(
         code=FailureCode.INTERACTION_REQUIRED,
         message="Confirm this capability invocation before continuing.",
         details={
             "kind": "confirmation",
             "title": "Confirmation required",
             "capability_id": "finance.send_payment",
             "hints": (),
         },
     )
     ```

2. **Caller Interaction:**
   - The caller UI (web prompt, CLI dialog, agent supervisor) presents the interaction request to a human operator.
   - The human approves and generates or retrieves a confirmation token.

3. **Second Invocation (Authorized):**
   - The caller re-invokes with `ExecutionContext(..., confirmation_evidence=ConfirmationEvidence(token))`.
   - `ConfirmationPolicy` forwards the evidence to the configured `ConfirmationVerifier`.
   - The verifier validates evidence against the exact `CapabilityId`, `Invocation.payload`, and `Principal`.
   - If valid -> `ConfirmationVerdict.VALID` -> `PolicySuccess` -> handler executes!

---

## 6. The Core Architectural Boundary

```text
Agnara Public Capability Contract
            │
            ▼
     Inspectable Metadata (Risk, Effects, Idempotency, Scopes, Confirmation)
            │
            ▼
========================================================================
                      APPLICATION BOUNDARY
========================================================================
            │
            ▼
     Local Policy Decision (Evaluation of built-in & application rules)
            │
            ▼
       Execution Choice (Execute / Deny / Demand Confirmation)
```

---

## 7. Policy Support Matrix: Empirical Evidence

| Feature | Declared | Inspectable | Agnara-enforced | App responsibility | Executable Evidence |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`scopes`** | `CapabilityDefinition.scopes` | `cap_def.scopes`, `describe_app` | **YES, if `ScopePolicy` attached.** | Attaching `ScopePolicy`; granting scopes to `Principal`. | `test_agnara_scope_policy.py` |
| **`effects`** | `CapabilityDefinition.effects` | `cap_def.effects`, `registry.with_effect()` | **NO.** Purely declarative in core. | Truthfully declaring effects; managing state mutation. | `test_idempotency_and_effects_semantics.py` |
| **`risk`** | `CapabilityDefinition.risk` | `cap_def.risk`, `describe_app` | **NO.** Core does not halt calls on Risk score alone. | Inspecting risk before invocation; requiring human approval. | `test_agnara_metadata_and_introspection.py` |
| **`idempotency`** | `CapabilityDefinition.idempotency` | `cap_def.idempotency`, `describe_app` | **NO.** Core does not deduplicate requests or cache calls. | Client/agent inspecting flag before retrying. | `test_idempotency_and_effects_semantics.py` |
| **`confirmation`** | `CapabilityDefinition.confirmation` | `cap_def.confirmation`, `describe_app` | **YES.** `compile()` checks verifier; halts with `INTERACTION_REQUIRED`. | Implementing `ConfirmationVerifier` protocol, issuing tokens. | `test_agnara_confirmation_enforcement.py` |
| **`policies`** | `CapabilityDefinition.policies` | `cap_def.policies`, `plan.policies` | **YES.** Evaluated sequentially; halts on `PolicyFailure`. | Defining business rules conforming to `agnara.Policy`. | `test_application_guardrails.py` |
