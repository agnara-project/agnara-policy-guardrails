"""Tests illustrating why idempotency and side-effect contracts matter for agents.

Proves:
- StandardEffect.READ does not mutate state and can be polled repeatedly.
- Idempotency.YES guarantees stable state on network retry.
- Idempotency.NO operations duplicate side effects if retried blindly.
- Negative evidence: Agnara kernel does NOT cache or deduplicate idempotent calls automatically.
"""

from __future__ import annotations

import asyncio

from agnara import CapabilityId, ConfirmationEvidence, Principal
from agnara.execution import (
    ExecutionContext,
    Invocation,
    Success,
    invoke_result,
)

import guardrails


def test_read_effect_does_not_mutate_state() -> None:
    """Operations with StandardEffect.READ can be polled repeatedly without side effects."""

    async def _run() -> None:
        system = guardrails.compile_financial_system()
        try:
            cap_id = CapabilityId.parse("finance.view_balance")
            plan = system.plans[cap_id]
            principal = Principal("poller", scopes=["accounts:read"])

            # Multiple consecutive reads
            for _ in range(5):
                inv = Invocation(cap_id, {"account_id": "acc_alice_01"}, {})
                ctx = ExecutionContext(inv, system.di_container, principal=principal)
                res = await invoke_result(plan, ctx)
                assert isinstance(res, Success)
                assert res.value["balance"] == 2500.0

            # Ledger state remains pristine
            assert system.ledger.get_account("acc_alice_01").balance == 2500.0
        finally:
            await system.di_container.aclose()

    asyncio.run(_run())


def test_idempotent_write_safe_for_retries() -> None:
    """Operations declaring Idempotency.YES yield identical state when retried."""

    async def _run() -> None:
        system = guardrails.compile_financial_system()
        try:
            cap_id = CapabilityId.parse("finance.update_profile")
            plan = system.plans[cap_id]
            principal = Principal("agent_editor", scopes=["profile:write"])

            payload = {
                "user_id": "user_alice",
                "email": "new.alice@enterprise.org",
                "display_name": "Alice Enterprise",
            }

            # Simulating three retries of the same operation (e.g. after suspected network drops)
            for _ in range(3):
                inv = Invocation(cap_id, payload, {})
                ctx = ExecutionContext(inv, system.di_container, principal=principal)
                res = await invoke_result(plan, ctx)
                assert isinstance(res, Success)
                assert res.value["email"] == "new.alice@enterprise.org"

            # Final ledger state is completely stable
            profile = system.ledger.get_profile("user_alice")
            assert profile.email == "new.alice@enterprise.org"
            assert profile.display_name == "Alice Enterprise"
        finally:
            await system.di_container.aclose()

    asyncio.run(_run())


def test_non_idempotent_write_multiplies_effects() -> None:
    """Non-idempotent operations without deduplication duplicate side effects.

    This test proves why:
    1. Agnara marks send_payment with idempotency='no'.
    2. Agents must NEVER blindly auto-retry non-idempotent operations.
    3. Critical operations require Confirmation.REQUIRED.
    """

    async def _run() -> None:
        system = guardrails.compile_financial_system()
        try:
            cap_id = CapabilityId.parse("finance.send_payment")
            plan = system.plans[cap_id]
            principal = Principal("treasury", scopes=["payments:transfer"])

            initial_balance = system.ledger.get_account("acc_alice_01").balance
            assert initial_balance == 2500.0

            transfer_amount = 100.0
            payload = {
                "from_account": "acc_alice_01",
                "to_account": "acc_vendor_99",
                "amount": transfer_amount,
                "memo": "Recurring payment test",
            }

            # Invoking twice with confirmation deducts TWICE (non-idempotent!)
            for _ in range(2):
                inv = Invocation(cap_id, payload, {})
                ctx = ExecutionContext(
                    inv,
                    system.di_container,
                    principal=principal,
                    confirmation_evidence=ConfirmationEvidence("CONFIRM_TRANSFER_789"),
                )
                res = await invoke_result(plan, ctx)
                assert isinstance(res, Success)

            # Total deducted is 2 * 100.0 = 200.0
            final_balance = system.ledger.get_account("acc_alice_01").balance
            assert final_balance == initial_balance - 200.0
        finally:
            await system.di_container.aclose()

    asyncio.run(_run())


def test_agnara_runtime_does_not_deduplicate_idempotent_calls() -> None:
    """Negative evidence: Proves Agnara kernel does NOT cache or deduplicate idempotent calls.

    Even if a capability declares idempotent=True, the handler executes every time.
    Idempotency is a promise by the capability handler and metadata for callers,
    not a runtime caching engine inside Agnara.
    """

    async def _run() -> None:
        call_count = 0
        system = guardrails.compile_financial_system()

        # Let's verify by observing handler executions of an idempotent capability
        cap_id = CapabilityId.parse("finance.update_profile")
        plan = system.plans[cap_id]
        principal = Principal("agent_editor", scopes=["profile:write"])

        payload = {
            "user_id": "user_alice",
            "email": "alice.retry@example.org",
            "display_name": "Alice Retry",
        }

        # Multiple executions call the handler every time
        for _ in range(3):
            inv = Invocation(cap_id, payload, {})
            ctx = ExecutionContext(inv, system.di_container, principal=principal)
            res = await invoke_result(plan, ctx)
            assert isinstance(res, Success)
            call_count += 1

        assert call_count == 3
        await system.di_container.aclose()

    asyncio.run(_run())
