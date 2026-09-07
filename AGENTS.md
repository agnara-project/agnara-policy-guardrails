# AGENTS.md — Operational Manual for Autonomous AI Agents

> **Audience:** Claude Code, OpenAI Codex, Antigravity, and other autonomous AI coding agents inspecting, maintaining, or extending this codebase.
> **Role:** Single source of operational truth for machine agents. For human-oriented documentation, see `README.md`.

---

## 1. Project Identity & Historical Context

- **Repository:** `agnara-project/agnara-policy-guardrails`
- **Designation:** **Agnara Historical Reference Application #007**
- **Framework Version:** Strictly pinned to **`agnara==0.1.0a3`**
- **Python Version:** **CPython >= 3.14** (designed for free-threaded compatibility under PEP 703)
- **Status:** **Historical / Frozen**
- **Mission:** Demonstrate how Agnara 0.1.0a3 represents machine-readable metadata (`scopes`, `effects`, `risk`, `idempotency`, `confirmation`) to evaluate whether an operation can be safely executed, differentiating declarative contract metadata from actual runtime enforcement.

---

## 2. Inviolable Architectural Invariants

1. **Do Not Upgrade Agnara:** Under no circumstances should `pyproject.toml` or `requirements.txt` be altered to reference versions later than `0.1.0a3` or unreleased development branches (`main`/`develop`).
2. **Never Describe Agnara Metadata as an Enforced Security Guarantee Unless the Public a3 Runtime Demonstrably Enforces It:**
   - Declaring `effects={"read"}` does not restrict database operations in the handler.
   - Declaring `risk="critical"` does not automatically block invocation in core runtime.
   - Declaring `idempotent=True` does not provide automatic request caching or deduplication.
   - Declaring `scopes={"..."}` on `@app.capability` is declarative authorization metadata (ADR 0008) and grants or enforces nothing unless coupled with `ScopePolicy`.
3. **Never Turn Application-Level Policy Logic into a Claimed Agnara Framework Capability:**
   - Agnara provides the `Policy` protocol, `ScopePolicy`, `ConfirmationPolicy`, and the execution loop in `_execute`.
   - Core Agnara does NOT have a standalone "Agnara Policy Engine" or dynamic policy DSL.
   - Custom guardrails (`DailySpendingLimitPolicy`, `SubscriptionActiveGuardrailPolicy`) are application-level policies, not framework features.
4. **Do Not Modernize This Repository Using Later Agnara Policy, Authorization, Risk, Confirmation, or Execution APIs:**
   - Preserve the exact behavior and APIs of `agnara==0.1.0a3`.
5. **No Speculative or External Integrations:**
   - The financial ledger must remain 100% local, simulated, thread-safe, and deterministic.
   - Do NOT add real payment APIs, external databases, cloud services, OAuth, IAM, or OPA.
6. **Strict Standard Library Purity (ADR 0004):**
   - Zero external dependencies for models or policies. Standard library dataclasses, `StrEnum`, and protocols only.
7. **Self-Contained Test Suite:**
   - Use standard `pytest` and `asyncio.run()`. Do NOT add `pytest-asyncio` or external testing plugins.

---

## 3. Metadata vs Enforcement: The Core Boundary

Agents inspecting or modifying this codebase must adhere strictly to the boundary between declaration, inspection, and runtime enforcement in `agnara==0.1.0a3`:

```
+─────────────────────────────────────────────────────────────────────────────+
|                     METADATA vs ENFORCEMENT BOUNDARY                        |
+─────────────────────────────────────────────────────────────────────────────+

  1. CAPABILITY DECLARATION (Authoring Metadata)
     What the developer declares:
     @app.capability(risk=Risk.HIGH, effects=["database-write", "destructive"],
                     idempotent=True, confirmation=Confirmation.REQUIRED,
                     scopes=["subscriptions:write"])

  2. INTROSPECTION & CONTRACT EXPORT (Inspection Surface)
     What Agnara inspects at startup and exports in AppDescriptor via describe_app():
     CapabilityDescriptor(id, risk, effects, idempotency, confirmation, scopes, inputs)
     - Consumed by agents and supervisors before deciding whether to call.

  3. AGNARA RUNTIME POLICY PIPELINE (Framework Execution Enforcement)
     What the Agnara kernel actually validates before handler execution:
     - Iterates plan.policies sequentially:
       * ScopePolicy: Enforces context.principal.scopes. Failure -> FORBIDDEN.
       * ConfirmationPolicy: Injects InteractionRequest if evidence is missing
         (FailureCode.INTERACTION_REQUIRED); verifies ConfirmationEvidence via
         ConfirmationVerifier. Failure -> FORBIDDEN.
     - Strict TypeSchema input validation.

  4. APPLICATION RESPONSIBILITY (Domain & Client Safety)
     What Agnara DOES NOT do and leaves to the application / agent:
     - Enforcing read-only isolation (handlers must truthfully avoid writes).
     - Halting on Risk level without explicit policies.
     - Caching or deduplicating idempotent calls (agent must manage retries).
     - Business guardrails (spending limits, cooldown rules via custom Policy).
```

---

## 4. Codebase Structure & Ownership

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

## 5. Permitted vs Forbidden Modifications

### Permitted Modifications
- Correcting factual errors in documentation or comments.
- Adding tests that verify previously untested a3 behavior without altering framework semantics.
- Enhancing agent skills in `.agents/skills/`.

### Forbidden Modifications
- Changing `agnara==0.1.0a3` to any other version or git ref.
- Claiming that `Risk` or `effects` automatically restrict runtime execution in core.
- Introducing external auth, IAM, or policy engines.
- Adding real financial endpoints or non-local dependencies.
- Modifying `app.capability` to simulate future features.

---

## 6. Reproducible Command Palette

Agents performing modifications, health checks, or code reviews must run commands using the local virtual environment:

```powershell
# 1. Clean Environment Initialization
py -3.14 -m venv .venv
.\.venv\Scripts\activate

# 2. Dependency Installation
python -m pip install -r requirements.txt
python -m pip install -e ".[dev]"

# 3. Dynamic Version Assertion
python -c "import agnara; assert agnara.__version__ == '0.1.0a3', f'Wrong version: {agnara.__version__}'"

# 4. Code Formatting & Quality Verification
ruff format --check .
ruff check .

# 5. Comprehensive Test Suite (20 tests)
pytest -v

# 6. Interactive CLI Demonstration
python app.py

# 7. Packaging Verification
pip wheel . --no-deps -w dist
Remove-Item -Recurse -Force dist
```

All verification commands (`pytest -v`, `ruff check .`, `ruff format --check .`, `python app.py`, `pip wheel`) must exit with return code `0`.

---

## 7. Decision Log: Public a3 Support Matrix

| Feature | Declared | Inspectable | Agnara-Enforced | Application Responsibility | Executable Evidence |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`scopes`** | `@app.capability(scopes=...)` | `cap_def.scopes`, `describe_app` | **YES, if `ScopePolicy` is attached.** Unattached scopes are not enforced (ADR 0008). | Attaching `ScopePolicy` to definition and granting scopes to `Principal`. | `test_agnara_scope_policy.py` |
| **`effects`** | `@app.capability(effects=...)` (`StandardEffect`) | `cap_def.effects`, `registry.with_effect()`, `describe_app` | **NO.** Core does not analyze code or enforce read-only semantics. | Truthfully declaring effects; managing transactional rollback if needed. | `test_agnara_metadata_and_introspection.py`, `test_idempotency_and_effects_semantics.py` |
| **`risk`** | `@app.capability(risk=...)` (`Risk`) | `cap_def.risk`, `describe_app` | **NO.** Core does not halt execution based on Risk score alone. | Inspecting risk before invocation; requiring supervisor approval when high/critical. | `test_agnara_metadata_and_introspection.py` |
| **`idempotency`** | `@app.capability(idempotent=...)` (`Idempotency`) | `cap_def.idempotency`, `describe_app` | **NO.** Core does not deduplicate requests or maintain an idempotency cache. | Client/agent inspecting flag before retrying; handling idempotency keys. | `test_idempotency_and_effects_semantics.py` |
| **`confirmation`** | `@app.capability(confirmation=...)` (`Confirmation`) | `cap_def.confirmation`, `describe_app` | **YES.** `compile()` requires verifier if `REQUIRED`; runtime halts with `INTERACTION_REQUIRED` if evidence missing. | Implementing `ConfirmationVerifier` protocol, issuing tokens, collecting evidence. | `test_agnara_confirmation_enforcement.py` |
| **`policies`** | `CapabilityDefinition.declare(policies=...)` | `cap_def.policies`, `plan.policies`, `describe_app` | **YES.** `_execute()` evaluates `plan.policies` sequentially; halts on `PolicyFailure` with `FORBIDDEN`. | Defining domain rules conforming to `agnara.Policy` protocol. | `test_application_guardrails.py` |
