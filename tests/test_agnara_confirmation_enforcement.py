"""Tests demonstrating Agnara 0.1.0a3 ConfirmationPolicy and ConfirmationVerifier enforcement.

Proves:
- Compile-time check: ExecutionPlan.compile requires confirmation_verifier
  for Confirmation.REQUIRED.
- Compile-time check: Confirmation.POLICY requires explicit policies.
- Runtime two-phase interaction: Missing evidence yields FailureCode.INTERACTION_REQUIRED.
- Rejection: Invalid confirmation evidence yields FailureCode.FORBIDDEN.
- Authorization: Valid confirmation evidence allows execution.
"""

from __future__ import annotations

import asyncio

import pytest
from agnara import (
    Agnara,
    CapabilityId,
    Confirmation,
    ConfirmationEvidence,
    DefinitionError,
    Principal,
)
from agnara.core.di import DIRegistry
from agnara.execution import (
    ExecutionContext,
    ExecutionPlan,
    Failure,
    FailureCode,
    Invocation,
    Success,
    invoke_result,
)

import guardrails


def test_compilation_requires_verifier_for_confirmation_required() -> None:
    """Compiling an execution plan for a Confirmation.REQUIRED capability requires a verifier."""
    system = guardrails.compile_financial_system()
    cap_def = system.registry[CapabilityId.parse("finance.send_payment")]

    # Attempting to compile without confirmation_verifier raises DefinitionError
    with pytest.raises(DefinitionError, match="requires a confirmation verifier"):
        ExecutionPlan.compile(
            definition=cap_def,
            registry=system.di_registry,
            confirmation_verifier=None,
        )


def test_compilation_requires_policies_for_confirmation_policy() -> None:
    """Declaring confirmation='policy' requires at least one explicit policy."""
    app = Agnara("policy_confirm_test")

    @app.capability(confirmation=Confirmation.POLICY)
    def test_func() -> str:
        return "ok"

    frozen = app.compile()
    di_reg = DIRegistry()

    with pytest.raises(
        DefinitionError, match="declares policy confirmation but has no explicit policies"
    ):
        ExecutionPlan.compile(frozen[CapabilityId.parse("policy_confirm_test.test_func")], di_reg)


def test_missing_confirmation_evidence_demands_interaction() -> None:
    """Invoking without confirmation evidence returns FailureCode.INTERACTION_REQUIRED."""

    async def _run() -> None:
        system = guardrails.compile_financial_system()
        try:
            cap_id = CapabilityId.parse("finance.send_payment")
            plan = system.plans[cap_id]

            payload = {
                "from_account": "acc_alice_01",
                "to_account": "acc_vendor_99",
                "amount": 100.0,
                "memo": "Test payment",
            }
            inv = Invocation(cap_id, payload, {})
            principal = Principal("alice", scopes=["payments:transfer"])
            ctx = ExecutionContext(inv, system.di_container, principal=principal)

            result = await invoke_result(plan, ctx)
            assert isinstance(result, Failure)
            assert result.code == FailureCode.INTERACTION_REQUIRED
            assert result.details["kind"] == "confirmation"
            assert result.details["capability_id"] == "finance.send_payment"
            assert "Confirm this capability invocation" in result.message
        finally:
            await system.di_container.aclose()

    asyncio.run(_run())


def test_invalid_confirmation_evidence_rejected() -> None:
    """Invoking with an invalid confirmation evidence token returns FailureCode.FORBIDDEN."""

    async def _run() -> None:
        system = guardrails.compile_financial_system()
        try:
            cap_id = CapabilityId.parse("finance.send_payment")
            plan = system.plans[cap_id]

            payload = {
                "from_account": "acc_alice_01",
                "to_account": "acc_vendor_99",
                "amount": 100.0,
                "memo": "Test payment",
            }
            inv = Invocation(cap_id, payload, {})
            principal = Principal("alice", scopes=["payments:transfer"])
            ctx = ExecutionContext(
                inv,
                system.di_container,
                principal=principal,
                confirmation_evidence=ConfirmationEvidence("INVALID_SECRET_TOKEN"),
            )

            result = await invoke_result(plan, ctx)
            assert isinstance(result, Failure)
            assert result.code == FailureCode.FORBIDDEN
            assert "confirmation evidence was rejected" in result.message

            # Verify audit record was created by verifier
            assert len(system.verifier.audit_log) == 1
            assert system.verifier.audit_log[0]["evidence_match"] is False
        finally:
            await system.di_container.aclose()

    asyncio.run(_run())


def test_valid_confirmation_evidence_authorizes_execution() -> None:
    """Invoking with valid confirmation evidence executes transfer successfully."""

    async def _run() -> None:
        system = guardrails.compile_financial_system()
        try:
            cap_id = CapabilityId.parse("finance.send_payment")
            plan = system.plans[cap_id]

            payload = {
                "from_account": "acc_alice_01",
                "to_account": "acc_vendor_99",
                "amount": 150.0,
                "memo": "Valid invoice",
            }
            inv = Invocation(cap_id, payload, {})
            principal = Principal("alice", scopes=["payments:transfer"])
            ctx = ExecutionContext(
                inv,
                system.di_container,
                principal=principal,
                confirmation_evidence=ConfirmationEvidence("CONFIRM_TRANSFER_789"),
            )

            result = await invoke_result(plan, ctx)
            assert isinstance(result, Success)
            assert result.value["amount"] == 150.0
            assert result.value["status"] == "completed"

            # Check ledger balances
            assert system.ledger.get_account("acc_alice_01").balance == 2350.0
            assert system.ledger.get_account("acc_vendor_99").balance == 300.0

            # Verify audit record was created by verifier
            assert len(system.verifier.audit_log) == 1
            assert system.verifier.audit_log[0]["evidence_match"] is True
        finally:
            await system.di_container.aclose()

    asyncio.run(_run())
