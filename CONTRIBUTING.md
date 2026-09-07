# Contributing to Agnara Historical Reference Application #007

Thank you for your interest in **Agnara Historical Reference Application #007 (`agnara-policy-guardrails`)**.

---

## 1. Repository Status: Historical / Frozen

> [!WARNING]
> This repository is an **immutable historical reference application**, intentionally pinned to **`agnara==0.1.0a3`** on **CPython >= 3.14**.
> It serves as a permanent reference demonstrating how Agnara 0.1.0a3 represents machine-readable metadata to evaluate whether an operation can be executed safely by humans and autonomous agents.

Because of this frozen status:
- **No API Modernization:** Pull requests updating the `agnara` dependency to newer releases will not be accepted.
- **No Speculative Extensions:** PRs adding features that did not exist in `agnara==0.1.0a3` will be rejected.
- **Allowed Contributions:** Only critical bug fixes to the reference example code, documentation clarity improvements, or test suite fixes that preserve reproduction under `agnara==0.1.0a3` and CPython >= 3.14 will be reviewed.

---

## 2. Local Development & Verification

Before submitting any documentation fix or issue report, verify that the test suite and demonstration run cleanly:

```powershell
# Create and activate virtual environment
py -3.14 -m venv .venv
.\.venv\Scripts\activate

# Install exact requirements and dev dependencies
python -m pip install -e ".[dev]"

# Run test suite
pytest -v

# Run linter and formatting checks
ruff check .
ruff format --check .

# Execute reference demonstration
python app.py
```

All commands must exit with status `0`.
