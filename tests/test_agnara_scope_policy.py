"""Tests demonstrating Agnara 0.1.0a3 ScopePolicy and scope authorization boundaries.

Proves:
- ScopePolicy evaluates principal.scopes against required scopes.
- Missing scopes yield FailureCode.FORBIDDEN with canonical missing scope details.
- Negative evidence: Declaring scopes without ScopePolicy grants/enforces nothing (ADR 0008).
"""

from __future__ import annotations

import asyncio

from agnara import (
    Agnara,
    AnonymousPrincipal,
    CapabilityId,
    Principal,
    ScopePolicy,
)
from agnara.core.di import DIContainer, DIRegistry
from agnara.execution import (
    ExecutionContext,
    ExecutionPlan,
    Failure,
    FailureCode,
    Invocation,
    Success,
    invoke_result,
)
from agnara.policy import PolicyFailure, PolicySuccess

import guardrails


def test_scope_policy_unit_evaluation() -> None:
    """ScopePolicy directly evaluates principal granted scopes."""

    async def _run() -> None:
        policy = ScopePolicy(["accounts:read", "audit:view"])

        # Missing all scopes
        ctx_anon = ExecutionContext(
            Invocation(CapabilityId.parse("test.probe"), {}, {}),
            di_container=None,  # type: ignore[arg-type]
            principal=AnonymousPrincipal(),
        )
        res_anon = await policy.evaluate(ctx_anon)
        assert isinstance(res_anon, PolicyFailure)
        assert "accounts:read" in res_anon.reason
        assert "audit:view" in res_anon.reason

        # Partial scopes
        ctx_partial = ExecutionContext(
            Invocation(CapabilityId.parse("test.probe"), {}, {}),
            di_container=None,  # type: ignore[arg-type]
            principal=Principal("user_1", scopes=["accounts:read"]),
        )
        res_partial = await policy.evaluate(ctx_partial)
        assert isinstance(res_partial, PolicyFailure)
        assert "missing required scopes: audit:view" in res_partial.reason

        # All scopes granted
        ctx_full = ExecutionContext(
            Invocation(CapabilityId.parse("test.probe"), {}, {}),
            di_container=None,  # type: ignore[arg-type]
            principal=Principal("user_1", scopes=["accounts:read", "audit:view", "extra:scope"]),
        )
        res_full = await policy.evaluate(ctx_full)
        assert isinstance(res_full, PolicySuccess)

    asyncio.run(_run())


def test_anonymous_principal_denied_access() -> None:
    """Anonymous caller invoking a capability guarded by ScopePolicy is denied with FORBIDDEN."""

    async def _run() -> None:
        system = guardrails.compile_financial_system()
        try:
            cap_id = CapabilityId.parse("finance.view_balance")
            plan = system.plans[cap_id]

            inv = Invocation(cap_id, {"account_id": "acc_alice_01"}, {})
            ctx = ExecutionContext(inv, system.di_container, principal=AnonymousPrincipal())

            result = await invoke_result(plan, ctx)
            assert isinstance(result, Failure)
            assert result.code == FailureCode.FORBIDDEN
            assert "missing required scopes: accounts:read" in result.message
        finally:
            await system.di_container.aclose()

    asyncio.run(_run())


def test_authorized_principal_succeeds() -> None:
    """Authenticated caller with the required scope succeeds."""

    async def _run() -> None:
        system = guardrails.compile_financial_system()
        try:
            cap_id = CapabilityId.parse("finance.view_balance")
            plan = system.plans[cap_id]

            inv = Invocation(cap_id, {"account_id": "acc_alice_01"}, {})
            principal = Principal("alice_agent", scopes=["accounts:read"])
            ctx = ExecutionContext(inv, system.di_container, principal=principal)

            result = await invoke_result(plan, ctx)
            assert isinstance(result, Success)
            assert result.value["balance"] == 2500.0
            assert result.value["currency"] == "USD"
        finally:
            await system.di_container.aclose()

    asyncio.run(_run())


def test_scopes_declaration_without_scope_policy_is_not_enforced() -> None:
    """Proves ADR 0008: Declaring scopes in @app.capability is declarative metadata only.

    Without attaching ScopePolicy, an unauthenticated anonymous principal can invoke
    the capability because Agnara core separates declaration from policy enforcement.
    """

    async def _run() -> None:
        raw_app = Agnara("scope_test")

        # Declares scopes, but NO ScopePolicy is attached
        @raw_app.capability(scopes=["super_admin:delete"])
        def unprotected_action() -> str:
            return "executed without check"

        frozen = raw_app.compile()
        di_reg = DIRegistry()
        plan = ExecutionPlan.compile(
            frozen[CapabilityId.parse("scope_test.unprotected_action")], di_reg
        )
        container = DIContainer(di_reg)

        # Anonymous principal has ZERO scopes
        inv = Invocation(plan.definition.id, {}, {})
        ctx = ExecutionContext(inv, container, principal=AnonymousPrincipal())

        # Succeeded! Because declaration != enforcement in a3!
        res = await invoke_result(plan, ctx)
        assert isinstance(res, Success)
        assert res.value == "executed without check"

        await container.aclose()

    asyncio.run(_run())
