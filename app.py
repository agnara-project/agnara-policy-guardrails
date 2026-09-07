"""Interactive educational demonstration for Agnara Historical Reference Application #007.

Demonstrates how Agnara 0.1.0a3 represents machine-readable metadata to evaluate
whether an operation can be executed safely by humans and autonomous agents:
  Metadata Inspection -> Policy Evaluation -> Interaction Handling -> Safe Execution

Usage:
    python app.py
"""

from __future__ import annotations

import asyncio

from agnara import (
    CapabilityId,
    ConfirmationEvidence,
    Principal,
)
from agnara.execution import (
    ExecutionContext,
    Failure,
    Invocation,
    Success,
    invoke_result,
)
from agnara.introspection import describe_app

import guardrails


def print_banner(title: str) -> None:
    """Print an educational section header."""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def print_step(step_number: int, title: str, description: str) -> None:
    """Print an educational sub-step."""
    print(f"\n[{step_number}] {title}")
    print(f"    {description}")


async def main() -> None:
    print_banner("AGNARA HISTORICAL REFERENCE APPLICATION #007: agnara-policy-guardrails")
    print("Misión: Demostrar cómo Agnara 0.1.0a3 representa información machine-readable")
    print("        para evaluar si una operación puede ejecutarse de forma segura.")
    print("Runtime: CPython >= 3.14 | Framework: agnara==0.1.0a3 (Historical/Frozen)")
    print("Concepto Central: 'Agent-Safe API' (Contratos, Efectos, Idempotencia y Políticas)")

    # -------------------------------------------------------------------------
    # PHASE 1: Machine-Readable Capability Discovery & Inspection
    # -------------------------------------------------------------------------
    print_banner("PHASE 1: AGENT DISCOVERY & CAPABILITY METADATA INSPECTION")
    print("Antes de invocar cualquier herramienta, un agente autónomo o supervisor")
    print("debe inspeccionar la metadata de las capabilities expuestas:")

    system = guardrails.compile_financial_system()
    app_descriptor = describe_app(
        system.app,
        system.plans.values(),
        dependencies=system.di_registry,
    )
    data = app_descriptor.json_data()

    print("\nResumen de Capabilities registradas en el namespace 'finance':")
    print(f"{'Capability ID':<28} {'Risk':<10} {'Effects':<30} {'Idempotent':<12} {'Confirm':<10}")
    print("-" * 92)
    for cap in data["capabilities"]:
        effects_str = ", ".join(cap["effects"])
        print(
            f"{cap['id']:<28} {cap['risk']:<10} {effects_str:<30} "
            f"{cap['idempotency']:<12} {cap['confirmation']:<10}"
        )

    # -------------------------------------------------------------------------
    # PHASE 2: Read-Only, Low-Risk Safe Operation (view_balance)
    # -------------------------------------------------------------------------
    print_banner("PHASE 2: READ-ONLY LOW RISK (view_balance)")
    print("Efectos: ['read'] | Risk: LOW | Idempotente: YES | Confirmación: NEVER")
    print("Las operaciones de lectura no mutan estado y son seguras para polling autónomo.")

    view_cap_id = CapabilityId.parse("finance.view_balance")
    view_plan = system.plans[view_cap_id]

    print_step(
        1,
        "Invocación Anónima (Sin scopes)",
        "Un llamador sin autenticar intenta leer el balance de la cuenta.",
    )
    inv_anon = Invocation(view_cap_id, {"account_id": "acc_alice_01"}, {})
    ctx_anon = ExecutionContext(inv_anon, system.di_container)
    res_anon = await invoke_result(view_plan, ctx_anon)
    print(f"    Resultado: {type(res_anon).__name__}")
    if isinstance(res_anon, Failure):
        print(f"    Código:    {res_anon.code.value} (HTTP 403 Forbidden)")
        print(f"    Mensaje:   {res_anon.message}")

    print_step(
        2,
        "Invocación con Principal Autorizado",
        "El agente presenta credenciales con el scope requerido 'accounts:read'.",
    )
    principal_reader = Principal("agent_analyst_01", scopes=["accounts:read"])
    ctx_reader = ExecutionContext(inv_anon, system.di_container, principal=principal_reader)
    res_reader = await invoke_result(view_plan, ctx_reader)
    print(f"    Resultado: {type(res_reader).__name__}")
    if isinstance(res_reader, Success):
        print(f"    Valor:     {res_reader.value}")

    # -------------------------------------------------------------------------
    # PHASE 3: Idempotent State Mutation (update_profile)
    # -------------------------------------------------------------------------
    print_banner("PHASE 3: IDEMPOTENT STATE MUTATION (update_profile)")
    print("Efectos: ['database-write'] | Risk: MEDIUM | Idempotente: YES")
    print("¿Por qué importa la idempotencia para agentes?")
    print("Si un agente experimenta un timeout de red, reintentar una operación idempotente")
    print("garantiza que el estado final sea coherente sin multiplicar efectos secundarios.")

    update_cap_id = CapabilityId.parse("finance.update_profile")
    update_plan = system.plans[update_cap_id]
    principal_writer = Principal("agent_profile_editor", scopes=["profile:write"])

    payload_update = {
        "user_id": "user_alice",
        "email": "alice.smith@example.org",
        "display_name": "Alice Smith Enterprise",
    }
    inv_update = Invocation(update_cap_id, payload_update, {})
    ctx_update_1 = ExecutionContext(inv_update, system.di_container, principal=principal_writer)

    print_step(1, "Primera Ejecución de update_profile", "Actualizando email y nombre.")
    res_up_1 = await invoke_result(update_plan, ctx_update_1)
    if isinstance(res_up_1, Success):
        print(f"    Resultado 1: {res_up_1.value}")

    print_step(2, "Reintento de update_profile (Simulando retry tras timeout)", "Mismo payload.")
    ctx_update_2 = ExecutionContext(inv_update, system.di_container, principal=principal_writer)
    res_up_2 = await invoke_result(update_plan, ctx_update_2)
    if isinstance(res_up_2, Success):
        print(f"    Resultado 2: {res_up_2.value}")
        print("    [SAFE] La llamada repetida no corrompió ni duplicó datos.")

    # -------------------------------------------------------------------------
    # PHASE 4: Destructive Action with Guardrail Policy (cancel_subscription)
    # -------------------------------------------------------------------------
    print_banner("PHASE 4: HIGH RISK & DESTRUCTIVE GUARDRAIL (cancel_subscription)")
    print("Efectos: ['database-write', 'destructive'] | Risk: HIGH")
    print("Requiere scope 'subscriptions:write' y la política 'SubscriptionActiveGuardrailPolicy'.")

    cancel_cap_id = CapabilityId.parse("finance.cancel_subscription")
    cancel_plan = system.plans[cancel_cap_id]
    principal_canceller = Principal("support_agent", scopes=["subscriptions:write"])

    print_step(
        1,
        "Intento de cancelación con motivo insuficiente",
        "Razón: 'no' (menor a 5 caracteres). Guardrail detiene la ejecución.",
    )
    inv_bad_reason = Invocation(
        cancel_cap_id,
        {"subscription_id": "sub_pro_101", "reason": "no"},
        {},
    )
    ctx_bad_reason = ExecutionContext(
        inv_bad_reason, system.di_container, principal=principal_canceller
    )
    res_bad_reason = await invoke_result(cancel_plan, ctx_bad_reason)
    if isinstance(res_bad_reason, Failure):
        print(f"    Guardrail Activado: {res_bad_reason.code.value}")
        print(f"    Razón:              {res_bad_reason.message}")

    print_step(
        2,
        "Cancelación válida con justificación completa",
        "Razón: 'Cliente migra a infraestructura on-premise'.",
    )
    inv_good_reason = Invocation(
        cancel_cap_id,
        {
            "subscription_id": "sub_pro_101",
            "reason": "Cliente migra a infraestructura on-premise",
        },
        {},
    )
    ctx_good_reason = ExecutionContext(
        inv_good_reason, system.di_container, principal=principal_canceller
    )
    res_good_reason = await invoke_result(cancel_plan, ctx_good_reason)
    if isinstance(res_good_reason, Success):
        print(f"    Cancelación exitosa: {res_good_reason.value}")

    # -------------------------------------------------------------------------
    # PHASE 5: Non-Idempotent Financial Write with Confirmation Flow (send_payment)
    # -------------------------------------------------------------------------
    print_banner("PHASE 5: FINANCIAL WRITE & TWO-PHASE CONFIRMATION (send_payment)")
    print("Efectos: ['financial-write'] | Risk: CRITICAL | Idempotente: NO")
    print("Confirmation: REQUIRED (El runtime exige evidencia antes de autorizar).")

    payment_cap_id = CapabilityId.parse("finance.send_payment")
    payment_plan = system.plans[payment_cap_id]
    principal_payer = Principal("agent_treasury", scopes=["payments:transfer"])

    payment_payload = {
        "from_account": "acc_alice_01",
        "to_account": "acc_vendor_99",
        "amount": 250.0,
        "memo": "Pago por servicios de hosting Q3",
    }
    inv_payment = Invocation(payment_cap_id, payment_payload, {})

    print_step(
        1,
        "Intento sin evidencia de confirmación",
        "El agente invoca directamente sin autorización previa.",
    )
    ctx_no_evidence = ExecutionContext(inv_payment, system.di_container, principal=principal_payer)
    res_no_evidence = await invoke_result(payment_plan, ctx_no_evidence)
    if isinstance(res_no_evidence, Failure):
        print(f"    Resultado:   {res_no_evidence.code.value} (INTERACTION_REQUIRED)")
        print(f"    Mensaje:     {res_no_evidence.message}")
        print(f"    Interaction: {dict(res_no_evidence.details)}")

    print_step(
        2,
        "Intento con evidencia de confirmación inválida / expirada",
        "El agente presenta un token no reconocido por el verifier.",
    )
    ctx_bad_evidence = ExecutionContext(
        inv_payment,
        system.di_container,
        principal=principal_payer,
        confirmation_evidence=ConfirmationEvidence("INVALID_TOKEN_XYZ"),
    )
    res_bad_evidence = await invoke_result(payment_plan, ctx_bad_evidence)
    if isinstance(res_bad_evidence, Failure):
        print(f"    Resultado:   {res_bad_evidence.code.value} (FORBIDDEN)")
        print(f"    Mensaje:     {res_bad_evidence.message}")

    print_step(
        3,
        "Límite de Gasto Superado (DailySpendingLimitPolicy)",
        "Intento de transferir $1,500 cuando el límite de guardrail es $1,000.",
    )
    inv_high_amount = Invocation(
        payment_cap_id,
        {
            "from_account": "acc_alice_01",
            "to_account": "acc_vendor_99",
            "amount": 1500.0,
            "memo": "Transferencia de alto volumen",
        },
        {},
    )
    ctx_high_amount = ExecutionContext(
        inv_high_amount,
        system.di_container,
        principal=principal_payer,
        confirmation_evidence=ConfirmationEvidence("CONFIRM_TRANSFER_789"),
    )
    res_high_amount = await invoke_result(payment_plan, ctx_high_amount)
    if isinstance(res_high_amount, Failure):
        print(f"    Límite Excedido: {res_high_amount.code.value}")
        print(f"    Mensaje:         {res_high_amount.message}")

    print_step(
        4,
        "Confirmación Válida y Transferencia Exitosa",
        "El humano supervisor autoriza con el token válido 'CONFIRM_TRANSFER_789'.",
    )
    ctx_valid = ExecutionContext(
        inv_payment,
        system.di_container,
        principal=principal_payer,
        confirmation_evidence=ConfirmationEvidence("CONFIRM_TRANSFER_789"),
    )
    res_valid = await invoke_result(payment_plan, ctx_valid)
    if isinstance(res_valid, Success):
        print("    Transferencia Ejecutada con Éxito:")
        for k, v in res_valid.value.items():
            print(f"      - {k:<15}: {v}")

    # Verificar estado del ledger
    acc_alice = system.ledger.get_account("acc_alice_01")
    acc_vendor = system.ledger.get_account("acc_vendor_99")
    print("\nBalances Actualizados en Ledger:")
    print(f"  - acc_alice_01:  ${acc_alice.balance:.2f}")
    print(f"  - acc_vendor_99: ${acc_vendor.balance:.2f}")

    # -------------------------------------------------------------------------
    # PHASE 6: Real Framework Guarantees vs Application Boundaries
    # -------------------------------------------------------------------------
    print_banner("PHASE 6: FRONTERA DE RESPONSABILIDADES EN AGNARA 0.1.0a3")
    print("Resumen de qué garantiza Agnara vs qué es responsabilidad de la aplicación:\n")
    print(f"{'Mecanismo':<22} {'Garantía en agnara==0.1.0a3':<34} {'Responsabilidad de la App'}")
    print("-" * 92)
    rows = [
        (
            "Scopes",
            "ScopePolicy valida principal.scopes",
            "Declarar scopes y asignar ScopePolicy",
        ),
        (
            "Confirmation",
            "Exige verifier y pide Interaction",
            "Implementar ConfirmationVerifier",
        ),
        (
            "Risk",
            "Metadata declarativa en Definition",
            "Evaluar el riesgo antes de invocar",
        ),
        (
            "Effects",
            "Metadata declarativa y consultas",
            "Asegurar que el handler cumpla efectos",
        ),
        (
            "Idempotency",
            "Tri-state (YES/NO/UNKNOWN)",
            "Manejo de claves y reintentos en cliente",
        ),
        (
            "Policies",
            "Pipeline secuencial asíncrono",
            "Definir reglas de negocio en Policy",
        ),
    ]
    for m, g, r in rows:
        print(f"{m:<22} {g:<34} {r}")
    print("-" * 92)

    await system.di_container.aclose()
    print("\nEjecución de demostración finalizada exitosamente.")


if __name__ == "__main__":
    asyncio.run(main())
