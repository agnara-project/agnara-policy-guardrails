"""Tests demonstrating Agnara 0.1.0a3 capability metadata and pre-execution introspection.

Proves:
- Metadata declaration: effects, risk, idempotency, confirmation, scopes.
- Machine-readable introspection via describe_app() and CapabilityDescriptor.
- Negative evidence: Risk and effects are purely declarative and do not block execution in core.
"""

from __future__ import annotations

import asyncio

from agnara import (
    Agnara,
    CapabilityId,
    Confirmation,
    Idempotency,
    Principal,
    Risk,
    StandardEffect,
)
from agnara.core.di import DIContainer, DIRegistry
from agnara.execution import ExecutionContext, ExecutionPlan, Invocation, Success, invoke_result
from agnara.introspection import describe_app

import guardrails


def test_registry_effects_filtering() -> None:
    """FrozenCapabilityRegistry allows querying capabilities by declared effects."""
    system = guardrails.compile_financial_system()
    registry = system.registry

    # 1. Query read-only capabilities
    read_caps = registry.with_effect(StandardEffect.READ.value)
    read_ids = {str(c.id) for c in read_caps}
    assert "finance.view_balance" in read_ids
    assert "finance.send_payment" not in read_ids

    # 2. Query destructive capabilities
    destructive_caps = registry.with_effect(StandardEffect.DESTRUCTIVE.value)
    destructive_ids = {str(c.id) for c in destructive_caps}
    assert "finance.cancel_subscription" in destructive_ids
    assert "finance.view_balance" not in destructive_ids

    # 3. Query financial write capabilities
    financial_caps = registry.with_effect(StandardEffect.FINANCIAL_WRITE.value)
    financial_ids = {str(c.id) for c in financial_caps}
    assert "finance.send_payment" in financial_ids
    assert "finance.update_profile" not in financial_ids


def test_describe_app_machine_readable_contract() -> None:
    """describe_app produces complete, protocol-neutral JSON schema descriptors."""
    system = guardrails.compile_financial_system()
    app_descriptor = describe_app(
        system.app,
        system.plans.values(),
        dependencies=system.di_registry,
    )
    json_data = app_descriptor.json_data()

    assert json_data["name"] == "finance"
    capabilities = {c["id"]: c for c in json_data["capabilities"]}
    assert len(capabilities) == 4

    # Check view_balance descriptor
    view_desc = capabilities["finance.view_balance"]
    assert view_desc["risk"] == Risk.LOW.value
    assert view_desc["effects"] == [StandardEffect.READ.value]
    assert view_desc["idempotency"] == Idempotency.YES.value
    assert view_desc["confirmation"] == Confirmation.NEVER.value
    assert view_desc["scopes"] == ["accounts:read"]
    assert len(view_desc["inputs"]) == 1
    assert view_desc["inputs"][0]["name"] == "account_id"
    assert view_desc["inputs"][0]["schema"] == {"type": "string"}

    # Check send_payment descriptor
    pay_desc = capabilities["finance.send_payment"]
    assert pay_desc["risk"] == Risk.CRITICAL.value
    assert pay_desc["effects"] == [StandardEffect.FINANCIAL_WRITE.value]
    assert pay_desc["idempotency"] == Idempotency.NO.value
    assert pay_desc["confirmation"] == Confirmation.REQUIRED.value
    assert pay_desc["scopes"] == ["payments:transfer"]
    input_names = {i["name"] for i in pay_desc["inputs"]}
    assert input_names == {"from_account", "to_account", "amount", "memo"}


def test_dependency_protected_from_inputs() -> None:
    """DI-injected dependencies like FinancialLedger are not exposed as inputs."""
    system = guardrails.compile_financial_system()
    app_descriptor = describe_app(
        system.app,
        system.plans.values(),
        dependencies=system.di_registry,
    )
    json_data = app_descriptor.json_data()

    for cap in json_data["capabilities"]:
        input_names = {i["name"] for i in cap["inputs"]}
        assert "ledger" not in input_names
        deps = [d["parameter"] for d in cap["dependencies"]]
        assert "ledger" in deps


def test_risk_metadata_is_declarative_only() -> None:
    """Proves that declaring Risk.CRITICAL does NOT automatically halt execution in core.

    Agnara treats Risk as declarative metadata for callers and operators.
    Without an explicit Policy or Confirmation.REQUIRED, the runtime executes normally.
    """

    async def _run() -> None:
        raw_app = Agnara("risk_test")

        @raw_app.capability(risk=Risk.CRITICAL)
        def dangerous_action(target: str) -> str:
            return f"executed on {target}"

        frozen = raw_app.compile()
        di_reg = DIRegistry()
        plan = ExecutionPlan.compile(
            frozen[CapabilityId.parse("risk_test.dangerous_action")], di_reg
        )
        container = DIContainer(di_reg)

        inv = Invocation(plan.definition.id, {"target": "production"}, {})
        ctx = ExecutionContext(inv, container, principal=Principal("anonymous_caller"))

        # In a3, Risk.CRITICAL alone DOES NOT block invocation!
        res = await invoke_result(plan, ctx)
        assert isinstance(res, Success)
        assert res.value == "executed on production"
        await container.aclose()

    asyncio.run(_run())
