# Agnara Historical Reference Application #007: `agnara-policy-guardrails`

[![Agnara Version](https://img.shields.io/badge/agnara-0.1.0a3-blue.svg)](https://pypi.org/project/agnara/0.1.0a3/)
[![Python](https://img.shields.io/badge/python-%3E%3D3.14-blue.svg)](https://www.python.org/)
[![Status](https://img.shields.io/badge/status-Historical%20%2F%20Frozen-lightgrey.svg)](#status--historical-freeze)
[![License](https://img.shields.io/badge/license-Apache--2.0-green.svg)](LICENSE)

> **The canonical reference application demonstrating how to build an `Agent-Safe API` using machine-readable contracts, operational guardrails, and execution policies in `agnara==0.1.0a3` on CPython >= 3.14.**

> [!WARNING]
> **Historical Baseline Warning:**
> This repository demonstrates the policy and safety metadata publicly available in **Agnara 0.1.0a3**. Metadata must not be interpreted as an enforcement guarantee unless explicitly demonstrated by the runtime.
>
> This repository is intentionally version-bound and must not be modernized to newer Agnara policy or guardrail APIs.

---

## 1. Mission & What Is an "Agent-Safe API"?

When autonomous AI agents or external orchestrators interact with application APIs, conventional RPC or REST endpoints present severe operational hazards:
- **Blind Side-Effects:** The caller cannot distinguish a safe read from a permanent database modification without parsing prose documentation.
- **Uncontrolled Retries:** On network timeouts, agents often auto-retry blindly. If an operation is non-idempotent (like a financial transfer), money or records are duplicated.
- **Uninspected High-Risk Actions:** Critical or destructive capabilities (like cancelling subscriptions or deleting tenants) can be invoked without a machine-readable confirmation gate.
- **Implicit Authorizations:** Permissions are often buried in session cookies or opaque HTTP filters rather than validated against formal principal contracts before handler invocation.

**In Agnara, an API is "Agent-Safe" because every capability carries standardized, protocol-neutral, machine-readable metadata** describing:
1. What side effects it causes (`effects`).
2. Its operational danger level (`risk`).
3. Whether it can be retried safely on network failure (`idempotency`).
4. Whether it mandates explicit caller/human confirmation before execution (`confirmation`).
5. Which security labels the principal must hold (`scopes`), evaluated by transport-neutral policies (`Policy`).

```
                              AGENT DISCOVERY & INSPECTION
               ┌────────────────────────────────────────────────────────┐
               │              describe_app() / Descriptors              │
               │   - Risk, Effects, Idempotency, Confirmation, Inputs   │
               └──────────────────────────┬─────────────────────────────┘
                                          │
                                          ▼  Pre-flight Decision
                       ┌─────────────────────────────────────┐
                       │ Does agent hold scope?              │
                       │ Is operation destructive / critical?│
                       │ Can it be safely retried?           │
                       └──────────────────┬──────────────────┘
                                          │
                                          ▼  Invocation
+───────────────────────────────────────────────────────────────────────────────────────+
|                             AGNARA RUNTIME POLICY PIPELINE                            |
+───────────────────────────────────────────────────────────────────────────────────────+
  1. ScopePolicy (Built-in)     ──> Checks context.principal.scopes vs required scopes
  2. Domain Custom Policies     ──> Spending limits, business status checks (Application-level)
  3. ConfirmationPolicy         ──> Injects InteractionRequest if evidence is missing;
     (Built-in Engine)              verifies ConfirmationEvidence token via Verifier
  4. Input Validation           ──> Strict TypeSchema validation (Agnara runtime)
  5. Handler Execution          ──> Executes business logic in FinancialLedger
```

---

## 2. Policy Support Matrix: Metadata vs. Enforcement

A central historical contribution of #007 is documenting the exact boundary between what `agnara==0.1.0a3` declares, what it introspects, what it actually enforces, and what remains application responsibility:

| Feature | Declared | Inspectable | Agnara-enforced | App responsibility | Evidence |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`scopes`** | `CapabilityDefinition.scopes` / `@app.capability` | `cap_def.scopes`, `describe_app` | **YES, if `ScopePolicy` attached.** Unattached scopes grant/deny nothing. | Attaching `ScopePolicy`; granting scopes to `Principal`. | [`test_agnara_scope_policy.py`](tests/test_agnara_scope_policy.py) |
| **`effects`** | `CapabilityDefinition.effects` (`StandardEffect`) | `cap_def.effects`, `registry.with_effect()`, `describe_app` | **NO.** Core does not analyze code or enforce read-only DB isolation. | Truthfully declaring effects; managing transactions and state. | [`test_idempotency_and_effects_semantics.py`](tests/test_idempotency_and_effects_semantics.py) |
| **`risk`** | `CapabilityDefinition.risk` (`Risk`) | `cap_def.risk`, `describe_app` | **NO.** Core does not halt calls on Risk score alone. | Inspecting risk before invocation; requiring human approval if high/critical. | [`test_agnara_metadata_and_introspection.py`](tests/test_agnara_metadata_and_introspection.py) |
| **`idempotency`** | `CapabilityDefinition.idempotency` (`Idempotency`) | `cap_def.idempotency`, `describe_app` | **NO.** Core does not deduplicate requests or maintain an idempotency cache. | Client/agent inspecting flag before retrying; handling deduplication tokens. | [`test_idempotency_and_effects_semantics.py`](tests/test_idempotency_and_effects_semantics.py) |
| **`confirmation`** | `CapabilityDefinition.confirmation` (`Confirmation`) | `cap_def.confirmation`, `describe_app` | **YES.** `compile()` demands verifier if `REQUIRED`; runtime halts with `INTERACTION_REQUIRED`. | Implementing `ConfirmationVerifier` protocol, issuing tokens, collecting evidence. | [`test_agnara_confirmation_enforcement.py`](tests/test_agnara_confirmation_enforcement.py) |
| **`policies`** | `CapabilityDefinition.policies` | `cap_def.policies`, `plan.policies`, `describe_app` | **YES.** `_execute()` evaluates `plan.policies` sequentially; halts on `PolicyFailure`. | Defining business rules conforming to `agnara.Policy` protocol. | [`test_application_guardrails.py`](tests/test_application_guardrails.py) |

---

## 3. The Four Conceptual Domain Cases

This application implements a completely local, fictitious financial ledger (`finance` namespace). It contains **zero external API calls and zero real money**, ensuring 100% reproducible execution:

| Capability ID | Risk | Declared Effects | Idempotent | Confirmation | Scopes | Runtime Policies Attached |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `finance.view_balance` | `LOW` | `["read"]` | `YES` | `NEVER` | `accounts:read` | `ScopePolicy` |
| `finance.update_profile` | `MEDIUM` | `["database-write"]` | `YES` | `NEVER` | `profile:write` | `ScopePolicy` |
| `finance.cancel_subscription` | `HIGH` | `["database-write", "destructive"]` | `YES` | `NEVER` | `subscriptions:write` | `ScopePolicy`, `SubscriptionActiveGuardrailPolicy` |
| `finance.send_payment` | `CRITICAL` | `["financial-write"]` | `NO` | `REQUIRED` | `payments:transfer` | `ScopePolicy`, `DailySpendingLimitPolicy`, `ConfirmationPolicy` |

### 1. `finance.view_balance` (Read-Only, Low Risk)
- **Concept:** Information retrieval with no side effects.
- **Agent Behavior:** Autonomous agents can poll this capability repeatedly and concurrently without state corruption or financial risk.

### 2. `finance.update_profile` (State Mutation, Idempotent Write)
- **Concept:** Mutates the user's email and display name in the database.
- **Why Idempotency Matters:** Network drops during distributed agent execution often leave the agent unsure if the request was processed. Because `idempotent=True`, the agent can safely re-send the update without side-effect amplification.

### 3. `finance.cancel_subscription` (High Risk, Destructive Effect)
- **Concept:** Revokes active enterprise subscriptions.
- **Guardrail:** The `destructive` effect warns agents and UI adapters that this action revokes privileges. A custom domain policy (`SubscriptionActiveGuardrailPolicy`) enforces that a cancellation reason of at least 5 characters is provided before touching domain records.

### 4. `finance.send_payment` (Financial Mutation, Non-Idempotent, Confirmation Required)
- **Concept:** Transfers funds between accounts.
- **Guardrails:**
  - `idempotent=False`: Explicitly alerts callers that auto-retrying will deduct money twice.
  - `DailySpendingLimitPolicy`: Rejects transfers above $1,000.00 unless the caller holds an elevated `payments:unlimited` scope.
  - `Confirmation.REQUIRED`: Core Agnara demands a `ConfirmationVerifier` at compile time and requires a valid `ConfirmationEvidence` token at execution time before deducting funds.

---

## 4. The Decision Flow: Framework vs. Application

It is vital to distinguish what steps belong to the Agnara framework versus what belongs to the example application:

```
Capability Declaration
    │
    ▼
Public Metadata (effects, risk, idempotency, confirmation, scopes)
    │
    ▼
Pre-Execution Inspection via describe_app()  [Agnara Framework]
    │
    ▼
Execution Context & Invocation               [Agnara Framework]
    │
    ▼
Runtime Policy Pipeline                      [Agnara Framework Evaluation Loop]
  ├─ 1. ScopePolicy                          [Agnara Built-in Policy]
  ├─ 2. DailySpendingLimitPolicy             [Application-Level Policy]
  ├─ 3. SubscriptionActiveGuardrailPolicy     [Application-Level Policy]
  └─ 4. ConfirmationPolicy                   [Agnara Built-in Policy]
    │
    ▼
Decision Outcome                             [Agnara Framework Projection]
  ├─ Allow: All policies returned PolicySuccess() -> Executes handler
  ├─ Reject: Any policy returned PolicyFailure() -> FailureCode.FORBIDDEN
  └─ Require Confirmation: Missing evidence -> FailureCode.INTERACTION_REQUIRED
```

---

## 5. Architectural Decisions & Unsupported Capabilities in `0.1.0a3`

During the research and audit of `agnara==0.1.0a3`, the following technical realities were confirmed:

1. **`@app.capability` Does Not Accept `policies`:**
   The decorator records declarative metadata only (`scopes`, `effects`, `risk`, `confirmation`, `idempotent`). To attach runtime enforcement policies, this application uses `register_guarded_capability()`, which calls `CapabilityDefinition.declare(..., policies=[...])`.
2. **No Kernel Idempotency Cache:**
   The `0.1.0a3` runtime does not maintain an in-memory cache or deduplicate incoming calls based on idempotency keys. `Idempotency` is an inspection contract for clients.
3. **No Automatic Risk-Based Execution Blocker:**
   Core Agnara does not automatically halt an invocation simply because its risk is `HIGH` or `CRITICAL`. Execution blocking requires an explicit policy (such as `ConfirmationPolicy` or custom guardrails).
4. **No Standalone "Policy Engine" Service:**
   Agnara provides the `Policy` protocol, `ScopePolicy`, `ConfirmationPolicy`, and the execution loop in `_execute`. There is no dynamic policy DSL or external policy daemon in core.
5. **No Synchronous Interactive Prompts in Policies:**
   Policies are transport-neutral and asynchronous. When confirmation is required, policies return `PolicyInteractionRequired`, halting execution so the outer caller/adapter can collect evidence.

---

## 6. Architecture & Component Structure

```
agnara-policy-guardrails/
├── .agents/
│   ├── AGENTS.md                                       # Agent registry metadata
│   └── skills/                                         # Specialized agent workflows
│       ├── policy-guardrails-validation/SKILL.md       # Policy & boundary verification workflow
│       ├── documentation/SKILL.md                      # Documentation sync and quality gates
│       └── testing/SKILL.md                            # Testing gates and negative evidence rules
├── .github/                                            # GitHub automation & templates
│   ├── ISSUE_TEMPLATE/                                 # Bug report and doc improvement forms
│   │   ├── bug_report.yml
│   │   └── documentation.yml
│   ├── PULL_REQUEST_TEMPLATE.md                        # Pull request validation checklist
│   ├── dependabot.yml                                  # Dependabot configuration ignoring agnara
│   └── workflows/ci.yml                                # CI workflow (CPython 3.14 on Ubuntu & Windows)
├── tests/                                              # Comprehensive test suite (20 tests)
│   ├── __init__.py
│   ├── test_agnara_metadata_and_introspection.py       # Metadata declaration & describe_app
│   ├── test_agnara_scope_policy.py                     # ScopePolicy and principal evaluation
│   ├── test_agnara_confirmation_enforcement.py         # Confirmation compilation check & interaction
│   ├── test_application_guardrails.py                  # Domain guardrails (spending limit, reason)
│   └── test_idempotency_and_effects_semantics.py       # Effects purity & non-idempotent duplicate calls
├── domain.py                                           # In-memory financial ledger & models
├── guardrails.py                                       # Policies, verifiers, and capability declarations
├── app.py                                              # Interactive educational CLI runner
├── pyproject.toml                                      # Hatchling packaging configuration
├── requirements.txt                                    # Exact pinned dependency: agnara==0.1.0a3
├── LICENSE                                             # Apache 2.0 License
├── README.md                                           # Comprehensive historical reference documentation
├── ARCHITECTURE.md                                     # Deep architectural breakdown of policy pipeline
├── CHANGELOG.md                                        # Historical release notes
├── CONTRIBUTING.md                                     # Frozen repo contribution guidelines
└── SECURITY.md                                         # Security boundaries and vulnerability disclosure
```

---

## 7. Installation & Verification

### Prerequisites
- **CPython >= 3.14** (tested on CPython 3.14.4)
- **PowerShell**, Bash, or any standard terminal

### Step-by-Step Setup

1. **Create and activate a clean virtual environment:**
   ```powershell
   py -3.14 -m venv .venv
   .\.venv\Scripts\activate
   ```

2. **Install exact pinned dependencies:**
   ```powershell
   python -m pip install -r requirements.txt
   python -m pip install -e ".[dev]"
   ```

3. **Verify exact Agnara version:**
   ```powershell
   python -c "import agnara; assert agnara.__version__ == '0.1.0a3'"
   ```

4. **Run the automated test suite (20 tests):**
   ```powershell
   pytest -v
   ```

5. **Run code quality checks:**
   ```powershell
   ruff check .
   ruff format --check .
   ```

6. **Run the interactive educational tour:**
   ```powershell
   python app.py
   ```

---

## 8. Status & Historical Freeze

This repository is an official **Agnara Historical Reference Application** (#007).

- **Framework Target:** `agnara==0.1.0a3`
- **Language Target:** Python 3.14+ (CPython 3.14.4)
- **Status:** **Historical / Frozen**
- **Lifecycle Policy:** This repository documents the exact architectural reality of `agnara==0.1.0a3`. It does not adopt APIs from newer preview releases or experimental branches. Changes are limited to security patches and documentation clarifications.