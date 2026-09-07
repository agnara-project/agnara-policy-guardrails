"""Policy guardrails, verification, and capability definitions for the financial service.

Demonstrates Agnara 0.1.0a3 capabilities:
- Machine-readable declarations: scopes, effects, risk, idempotency, confirmation
- Policy protocol implementations: ScopePolicy, DailySpendingLimitPolicy,
  SubscriptionActiveGuardrailPolicy
- ConfirmationVerifier protocol and two-phase interaction flows
- Startup compilation and execution plan creation
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any

from agnara import (
    Agnara,
    CapabilityDefinition,
    CapabilityId,
    Confirmation,
    ConfirmationEvidence,
    ConfirmationVerdict,
    FrozenCapabilityRegistry,
    Idempotency,
    Policy,
    PolicyFailure,
    PolicyResult,
    PolicySuccess,
    Principal,
    Risk,
    ScopePolicy,
    StandardEffect,
)
from agnara._frozen import frozen_slots_dataclass
from agnara.core.di import DIContainer, DIRegistry, Scope, provider
from agnara.execution import (
    ExecutionContext,
    ExecutionPlan,
    Invocation,
)

from domain import FinancialLedger

# -----------------------------------------------------------------------------
# 1. Custom Application Policies (agnara.Policy Protocol)
# -----------------------------------------------------------------------------


@frozen_slots_dataclass
class DailySpendingLimitPolicy:
    """Policy guardrail checking transaction amounts against a spending threshold.

    Evaluated synchronously before handler execution.
    If the transaction amount exceeds `max_amount`, execution is denied with
    a PolicyFailure unless the principal holds the 'payments:unlimited' scope.
    """

    max_amount: float

    async def evaluate(self, context: ExecutionContext) -> PolicyResult:
        payload = context.invocation.payload
        amount = payload.get("amount")

        if isinstance(amount, (int, float)):
            if amount > self.max_amount:
                principal = context.principal
                if "payments:unlimited" not in principal.scopes:
                    return PolicyFailure(
                        f"transaction amount {amount:.2f} "
                        f"exceeds spending limit {self.max_amount:.2f}"
                    )
        return PolicySuccess()


@frozen_slots_dataclass
class SubscriptionActiveGuardrailPolicy:
    """Policy guardrail enforcing business safety rules for subscription cancellation.

    Ensures that high-risk destructive cancellations include an explicit explanation.
    """

    min_reason_length: int = 5

    async def evaluate(self, context: ExecutionContext) -> PolicyResult:
        payload = context.invocation.payload
        reason = payload.get("reason")

        if not isinstance(reason, str) or len(reason.strip()) < self.min_reason_length:
            return PolicyFailure(
                f"cancellation reason must be at least {self.min_reason_length} characters"
            )
        return PolicySuccess()


# -----------------------------------------------------------------------------
# 2. Confirmation Verifier (agnara.ConfirmationVerifier Protocol)
# -----------------------------------------------------------------------------


class FinancialConfirmationVerifier:
    """Verifies confirmation evidence tokens for high-risk capabilities.

    In Agnara 0.1.0a3, confirmation verifiers own evidence authenticity,
    input binding, and replay detection.
    """

    def __init__(self, valid_secret: str = "CONFIRM_TRANSFER_789") -> None:
        self.valid_secret = valid_secret
        self.audit_log: list[dict[str, Any]] = []

    async def verify(
        self,
        evidence: ConfirmationEvidence,
        *,
        capability_id: CapabilityId,
        invocation: Invocation,
        principal: Principal,
    ) -> ConfirmationVerdict:
        """Verify the evidence token against this exact capability and invocation."""
        is_valid = evidence.value == self.valid_secret

        self.audit_log.append(
            {
                "capability_id": str(capability_id),
                "principal": principal.identity,
                "evidence_match": is_valid,
                "amount": invocation.payload.get("amount"),
            }
        )

        if is_valid:
            return ConfirmationVerdict.VALID
        return ConfirmationVerdict.INVALID


# -----------------------------------------------------------------------------
# 3. Capability Handlers
# -----------------------------------------------------------------------------


def view_balance(account_id: str, ledger: FinancialLedger) -> dict[str, Any]:
    """View the current ledger balance and currency for an account."""
    account = ledger.get_account(account_id)
    return {
        "account_id": account.account_id,
        "owner_id": account.owner_id,
        "balance": account.balance,
        "currency": account.currency,
    }


def update_profile(
    user_id: str,
    email: str,
    display_name: str,
    ledger: FinancialLedger,
) -> dict[str, Any]:
    """Idempotently update user profile information in the system database."""
    profile = ledger.update_profile(user_id, email, display_name)
    return {
        "user_id": profile.user_id,
        "email": profile.email,
        "display_name": profile.display_name,
        "tier": profile.tier,
    }


def cancel_subscription(
    subscription_id: str,
    reason: str,
    ledger: FinancialLedger,
) -> dict[str, Any]:
    """Revoke an active subscription. Destructive action affecting service access."""
    sub = ledger.cancel_subscription(subscription_id, reason)
    return {
        "subscription_id": sub.subscription_id,
        "user_id": sub.user_id,
        "plan_name": sub.plan_name,
        "status": sub.status.value,
        "cancellation_reason": sub.cancellation_reason,
    }


def send_payment(
    from_account: str,
    to_account: str,
    amount: float,
    memo: str,
    ledger: FinancialLedger,
) -> dict[str, Any]:
    """Transfer financial balance between accounts. Irreversible non-idempotent operation."""
    receipt = ledger.transfer(from_account, to_account, amount, memo)
    return {
        "payment_id": receipt.payment_id,
        "from_account": receipt.from_account,
        "to_account": receipt.to_account,
        "amount": receipt.amount,
        "currency": receipt.currency,
        "status": receipt.status,
        "memo": receipt.memo,
        "audit_ref": receipt.audit_ref,
    }


# -----------------------------------------------------------------------------
# 4. Authoring & Guardrail Registration Helper
# -----------------------------------------------------------------------------


def register_guarded_capability[F: Callable[..., Any]](
    app: Agnara,
    func: F,
    *,
    name: str | None = None,
    description: str | None = None,
    scopes: Iterable[str] = (),
    effects: Iterable[str] = (),
    risk: Risk | str = Risk.LOW,
    confirmation: Confirmation | str = Confirmation.NEVER,
    idempotent: bool | None = None,
    policies: Iterable[Policy] = (),
) -> F:
    """Register a capability with both declarative metadata and runtime policies.

    In Agnara 0.1.0a3, `@app.capability` records metadata but does not accept
    a `policies` argument; `CapabilityDefinition.declare` accepts `policies`.
    This helper bridges the authoring convenience with runtime policy binding.
    """
    cap_name = name if name is not None else getattr(func, "__name__", "")
    cap_id = CapabilityId(namespace=app.name, name=cap_name)

    idempotency_state = (
        Idempotency.UNKNOWN
        if idempotent is None
        else (Idempotency.YES if idempotent else Idempotency.NO)
    )

    definition = CapabilityDefinition.declare(
        id=cap_id,
        handler=func,
        description=description or func.__doc__,
        scopes=scopes,
        effects=effects,
        risk=risk,
        confirmation=confirmation,
        idempotency=idempotency_state,
        policies=policies,
    )
    app.capabilities.register(definition)
    return func


def create_finance_app() -> Agnara:
    """Create and configure the Agnara application with all 4 reference capabilities."""
    app = Agnara("finance")

    # 1. view_balance: Read-only, Low Risk, Idempotent, Never confirms
    register_guarded_capability(
        app,
        view_balance,
        name="view_balance",
        description="View the current ledger balance and currency for an account.",
        scopes=["accounts:read"],
        effects=[StandardEffect.READ.value],
        risk=Risk.LOW,
        confirmation=Confirmation.NEVER,
        idempotent=True,
        policies=[ScopePolicy(["accounts:read"])],
    )

    # 2. update_profile: Database Write, Medium Risk, Idempotent, Never confirms
    register_guarded_capability(
        app,
        update_profile,
        name="update_profile",
        description="Idempotently update user profile information in the system database.",
        scopes=["profile:write"],
        effects=[StandardEffect.DATABASE_WRITE.value],
        risk=Risk.MEDIUM,
        confirmation=Confirmation.NEVER,
        idempotent=True,
        policies=[ScopePolicy(["profile:write"])],
    )

    # 3. cancel_subscription: Database Write + Destructive, High Risk, Idempotent
    register_guarded_capability(
        app,
        cancel_subscription,
        name="cancel_subscription",
        description="Revoke an active subscription. Destructive action affecting service access.",
        scopes=["subscriptions:write"],
        effects=[StandardEffect.DATABASE_WRITE.value, StandardEffect.DESTRUCTIVE.value],
        risk=Risk.HIGH,
        confirmation=Confirmation.NEVER,
        idempotent=True,
        policies=[
            ScopePolicy(["subscriptions:write"]),
            SubscriptionActiveGuardrailPolicy(min_reason_length=5),
        ],
    )

    # 4. send_payment: Financial Write, Critical Risk, Non-Idempotent, Requires Confirmation
    register_guarded_capability(
        app,
        send_payment,
        name="send_payment",
        description=(
            "Transfer financial balance between accounts. Irreversible non-idempotent operation."
        ),
        scopes=["payments:transfer"],
        effects=[StandardEffect.FINANCIAL_WRITE.value],
        risk=Risk.CRITICAL,
        confirmation=Confirmation.REQUIRED,
        idempotent=False,
        policies=[
            ScopePolicy(["payments:transfer"]),
            DailySpendingLimitPolicy(max_amount=1000.0),
        ],
    )

    return app


# -----------------------------------------------------------------------------
# 5. System Compilation (Composition Root)
# -----------------------------------------------------------------------------


@dataclass(slots=True)
class CompiledFinancialSystem:
    """Bundle containing compiled plans, frozen registry, and DI container."""

    app: Agnara
    registry: FrozenCapabilityRegistry
    plans: dict[CapabilityId, ExecutionPlan]
    di_registry: DIRegistry
    di_container: DIContainer
    ledger: FinancialLedger
    verifier: FinancialConfirmationVerifier


def compile_financial_system(
    ledger: FinancialLedger | None = None,
    verifier: FinancialConfirmationVerifier | None = None,
) -> CompiledFinancialSystem:
    """Compile the entire financial system into immutable plans ready for execution."""
    app = create_finance_app()
    frozen_caps = app.compile()

    shared_ledger = ledger if ledger is not None else FinancialLedger()
    confirmation_verifier = verifier if verifier is not None else FinancialConfirmationVerifier()

    # DI bindings
    di_reg = DIRegistry()

    @provider(scope=Scope.SINGLETON)
    def provide_ledger() -> FinancialLedger:
        return shared_ledger

    di_reg.bind(FinancialLedger, provide_ledger)
    di_container = DIContainer(di_reg)

    # Compile execution plans for all registered capabilities
    plans: dict[CapabilityId, ExecutionPlan] = {}
    for cap_id in frozen_caps:
        cap_def = frozen_caps[cap_id]
        plan = ExecutionPlan.compile(
            definition=cap_def,
            registry=di_reg,
            confirmation_verifier=confirmation_verifier
            if cap_def.confirmation is Confirmation.REQUIRED
            else None,
        )
        plans[cap_id] = plan

    return CompiledFinancialSystem(
        app=app,
        registry=frozen_caps,
        plans=plans,
        di_registry=di_reg,
        di_container=di_container,
        ledger=shared_ledger,
        verifier=confirmation_verifier,
    )
