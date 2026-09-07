"""Domain entities and local in-memory ledger for the financial reference service.

Designed with standard library purity (ADR 0004), zero external dependencies,
and strict thread safety for free-threaded CPython (PEP 703).
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from enum import StrEnum
from uuid import uuid4


class DomainError(Exception):
    """Base domain exception for financial service errors."""


class AccountNotFoundError(DomainError):
    """Raised when an account does not exist."""


class InsufficientFundsError(DomainError):
    """Raised when an account lacks sufficient balance for an operation."""


class SubscriptionNotFoundError(DomainError):
    """Raised when a subscription is not found."""


class SubscriptionAlreadyCancelledError(DomainError):
    """Raised when attempting to cancel an already cancelled subscription."""


class SubscriptionStatus(StrEnum):
    """Subscription lifecycle state."""

    ACTIVE = "active"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


@dataclass(slots=True)
class Account:
    """Financial account representing funds."""

    account_id: str
    owner_id: str
    balance: float
    currency: str = "USD"


@dataclass(slots=True)
class UserProfile:
    """User profile information."""

    user_id: str
    email: str
    display_name: str
    tier: str = "standard"


@dataclass(slots=True)
class Subscription:
    """Subscription contract for recurring capabilities."""

    subscription_id: str
    user_id: str
    plan_name: str
    status: SubscriptionStatus
    cancellation_reason: str | None = None


@dataclass(slots=True)
class PaymentReceipt:
    """Immutable receipt generated after a successful fund transfer."""

    payment_id: str
    from_account: str
    to_account: str
    amount: float
    currency: str
    status: str
    memo: str
    audit_ref: str


class FinancialLedger:
    """Thread-safe, local in-memory financial repository.

    Simulates an isolated financial backend without external network calls
    or real-world money.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._accounts: dict[str, Account] = {}
        self._profiles: dict[str, UserProfile] = {}
        self._subscriptions: dict[str, Subscription] = {}
        self._payments: list[PaymentReceipt] = []
        self._seed_initial_data()

    def _seed_initial_data(self) -> None:
        """Seed initial deterministic state for reproducible tests and demos."""
        self._accounts["acc_alice_01"] = Account(
            account_id="acc_alice_01",
            owner_id="user_alice",
            balance=2500.0,
            currency="USD",
        )
        self._accounts["acc_vendor_99"] = Account(
            account_id="acc_vendor_99",
            owner_id="vendor_external",
            balance=150.0,
            currency="USD",
        )
        self._profiles["user_alice"] = UserProfile(
            user_id="user_alice",
            email="alice@example.org",
            display_name="Alice L.",
            tier="premium",
        )
        self._subscriptions["sub_pro_101"] = Subscription(
            subscription_id="sub_pro_101",
            user_id="user_alice",
            plan_name="pro-enterprise",
            status=SubscriptionStatus.ACTIVE,
        )

    def get_account(self, account_id: str) -> Account:
        """Retrieve an account by ID."""
        with self._lock:
            account = self._accounts.get(account_id)
            if account is None:
                raise AccountNotFoundError(f"Account '{account_id}' was not found.")
            return Account(
                account_id=account.account_id,
                owner_id=account.owner_id,
                balance=account.balance,
                currency=account.currency,
            )

    def get_profile(self, user_id: str) -> UserProfile:
        """Retrieve a user profile by ID."""
        with self._lock:
            profile = self._profiles.get(user_id)
            if profile is None:
                raise DomainError(f"User profile '{user_id}' was not found.")
            return UserProfile(
                user_id=profile.user_id,
                email=profile.email,
                display_name=profile.display_name,
                tier=profile.tier,
            )

    def update_profile(self, user_id: str, email: str, display_name: str) -> UserProfile:
        """Update profile fields idempotently.

        Calling this multiple times with the exact same arguments produces
        the exact same state without side-effect amplification.
        """
        with self._lock:
            profile = self._profiles.get(user_id)
            if profile is None:
                # Upsert behavior maintains idempotency
                profile = UserProfile(
                    user_id=user_id,
                    email=email,
                    display_name=display_name,
                    tier="standard",
                )
                self._profiles[user_id] = profile
            else:
                profile.email = email
                profile.display_name = display_name
            return UserProfile(
                user_id=profile.user_id,
                email=profile.email,
                display_name=profile.display_name,
                tier=profile.tier,
            )

    def get_subscription(self, subscription_id: str) -> Subscription:
        """Retrieve a subscription by ID."""
        with self._lock:
            sub = self._subscriptions.get(subscription_id)
            if sub is None:
                raise SubscriptionNotFoundError(f"Subscription '{subscription_id}' was not found.")
            return Subscription(
                subscription_id=sub.subscription_id,
                user_id=sub.user_id,
                plan_name=sub.plan_name,
                status=sub.status,
                cancellation_reason=sub.cancellation_reason,
            )

    def cancel_subscription(self, subscription_id: str, reason: str) -> Subscription:
        """Cancel an active subscription.

        Idempotent: if already cancelled with reason, returning the existing
        record preserves stable state.
        """
        with self._lock:
            sub = self._subscriptions.get(subscription_id)
            if sub is None:
                raise SubscriptionNotFoundError(f"Subscription '{subscription_id}' was not found.")
            sub.status = SubscriptionStatus.CANCELLED
            sub.cancellation_reason = reason
            return Subscription(
                subscription_id=sub.subscription_id,
                user_id=sub.user_id,
                plan_name=sub.plan_name,
                status=sub.status,
                cancellation_reason=sub.cancellation_reason,
            )

    def transfer(
        self,
        from_account: str,
        to_account: str,
        amount: float,
        memo: str,
    ) -> PaymentReceipt:
        """Transfer balance from one account to another.

        NON-IDEMPOTENT operation: executing this method N times will deduct
        the amount N times. This is why financial operations require strict
        confirmation guardrails and idempotency metadata warnings for agents.
        """
        if amount <= 0:
            raise DomainError(f"Transfer amount must be positive, got {amount}.")

        with self._lock:
            source = self._accounts.get(from_account)
            if source is None:
                raise AccountNotFoundError(f"Source account '{from_account}' was not found.")
            target = self._accounts.get(to_account)
            if target is None:
                raise AccountNotFoundError(f"Target account '{to_account}' was not found.")

            if source.balance < amount:
                raise InsufficientFundsError(
                    f"Account '{from_account}' has insufficient balance "
                    f"({source.balance:.2f} < {amount:.2f})."
                )

            # Atomic in-memory balance transition
            source.balance -= amount
            target.balance += amount

            receipt = PaymentReceipt(
                payment_id=f"pay_{uuid4().hex[:10]}",
                from_account=from_account,
                to_account=to_account,
                amount=amount,
                currency=source.currency,
                status="completed",
                memo=memo,
                audit_ref=f"audit_{uuid4().hex[:8]}",
            )
            self._payments.append(receipt)
            return receipt
