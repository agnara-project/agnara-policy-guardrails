# Agent Skills & Verification Registry

This directory contains specialized agent context and skills for **Agnara Historical Reference Application #007 (`agnara-policy-guardrails`)**.

## Pinned Baseline
- Framework: `agnara==0.1.0a3`
- Runtime: CPython >= 3.14
- Status: Historical / Frozen

## Critical Invariants
1. Never describe Agnara metadata as an enforced security guarantee unless the public a3 runtime demonstrably enforces it.
2. Never turn application-level policy logic into a claimed Agnara framework capability.
3. Do not modernize this repository using later Agnara policy, authorization, risk, confirmation, or execution APIs.
4. Keep tests clean, self-contained, using `asyncio.run()` without external pytest plugins.
5. Verify tests and linting before committing:
   - `pytest -v`
   - `ruff check .`
   - `ruff format --check .`
   - `python app.py`
