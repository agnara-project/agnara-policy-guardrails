"""Tests demonstrating example application-level policies conforming to agnara.Policy protocol.

Proves:
- Custom application guardrails evaluate during ExecutionPlan execution.
- DailySpendingLimitPolicy denies transfers above threshold with FailureCode.FORBIDDEN.
- Elevated scope ('payments:unlimited') allows policy bypass.
- SubscriptionActiveGuardrailPolicy requires business justification for destructive actions.
"""

from __future__ import annotations

import asyncio

from agnara import CapabilityId, ConfirmationEvidence, Principal
from agnara.execution import (
    ExecutionContext,
    Failure,
    FailureCode,
    Invocation,
    Success,
    invoke_result,
)
from agnara.policy import PolicyFailure, PolicySuccess

import guardrails


def test_spending_limit_policy_unit() -> None:
    """DailySpendingLimitPolicy enforces threshold based on invocation payload."""

    async def _run() -> None:
        policy = guardrails.DailySpendingLimitPolicy(max_amount=500.0)

        # 1. Below threshold
        inv_low = Invocation(CapabilityId.parse("test.pay"), {"amount": 250.0}, {})
        ctx_low = ExecutionContext(inv_low, None, principal=Principal("user1"))  # type: ignore[arg-type]
        res_low = await policy.evaluate(ctx_low)
        assert isinstance(res_low, PolicySuccess)

        # 2. Above threshold without override scope
        inv_high = Invocation(CapabilityId.parse("test.pay"), {"amount": 750.0}, {})
        ctx_high = ExecutionContext(inv_high, None, principal=Principal("user1"))  # type: ignore[arg-type]
        res_high = await policy.evaluate(ctx_high)
        assert isinstance(res_high, PolicyFailure)
        assert "exceeds spending limit 500.00" in res_high.reason

        # 3. Above threshold with 'payments:unlimited' scope
        ctx_override = ExecutionContext(
            inv_high,
            None,  # type: ignore[arg-type]
            principal=Principal("admin_user", scopes=["payments:unlimited"]),
        )
        res_override = await policy.evaluate(ctx_override)
        assert isinstance(res_override, PolicySuccess)

    asyncio.run(_run())


def test_spending_limit_integration_in_pipeline() -> None:
    """Policy evaluation occurs before ConfirmationPolicy or handler execution."""

    async def _run() -> None:
        system = guardrails.compile_financial_system()
        try:
            cap_id = CapabilityId.parse("finance.send_payment")
            plan = system.plans[cap_id]

            # Transfer of $1200 exceeds $1000 limit
            payload = {
                "from_account": "acc_alice_01",
                "to_account": "acc_vendor_99",
                "amount": 1200.0,
                "memo": "Large transaction",
            }
            inv = Invocation(cap_id, payload, {})
            principal = Principal("user_treasury", scopes=["payments:transfer"])
            # Even with valid confirmation evidence, the policy stops execution first!
            ctx = ExecutionContext(
                inv,
                system.di_container,
                principal=principal,
                confirmation_evidence=ConfirmationEvidence("CONFIRM_TRANSFER_789"),
            )

            result = await invoke_result(plan, ctx)
            assert isinstance(result, Failure)
            assert result.code == FailureCode.FORBIDDEN
            assert "transaction amount 1200.00 exceeds spending limit 1000.00" in result.message
        finally:
            await system.di_container.aclose()

    asyncio.run(_run())


def test_subscription_guardrail_policy_cancellation_reason() -> None:
    """SubscriptionActiveGuardrailPolicy stops cancellation if reason is insufficient."""

    async def _run() -> None:
        system = guardrails.compile_financial_system()
        try:
            cap_id = CapabilityId.parse("finance.cancel_subscription")
            plan = system.plans[cap_id]

            principal = Principal("support_agent", scopes=["subscriptions:write"])

            # Reason too short (< 5 chars)
            inv_short = Invocation(
                cap_id,
                {"subscription_id": "sub_pro_101", "reason": "bye"},
                {},
            )
            ctx_short = ExecutionContext(inv_short, system.di_container, principal=principal)
            res_short = await invoke_result(plan, ctx_short)
            assert isinstance(res_short, Failure)
            assert res_short.code == FailureCode.FORBIDDEN
            assert "cancellation reason must be at least 5 characters" in res_short.message

            # Valid reason
            inv_valid = Invocation(
                cap_id,
                {
                    "subscription_id": "sub_pro_101",
                    "reason": "Customer no longer needs team seats",
                },
                {},
            )
            ctx_valid = ExecutionContext(inv_valid, system.di_container, principal=principal)
            res_valid = await invoke_result(plan, ctx_valid)
            assert isinstance(res_valid, Success)
            assert res_valid.value["status"] == "cancelled"
        finally:
            await system.di_container.aclose()

    asyncio.run(_run())
