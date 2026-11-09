# Contributing to quarantine-ledger

Thank you for your interest in improving `quarantine-ledger`! We welcome contributions that help teams keep test quarantines visible, bounded, and accountable.

## Design Philosophy & Invariants

Before proposing changes, please keep the project's core invariants in mind:

1. **Zero runtime dependencies**: The package relies strictly on the Python 3.11+ standard library (`tomllib`, `argparse`, `datetime`, `urllib.parse`, etc.).
2. **Never alter test outcomes**: `quarantine-ledger` is an accountability and CI gate tool. It does not skip, `xfail`, retry, or delete tests, and does not open issues or send notifications.
3. **No network calls**: Everything runs offline. Issue URLs are only checked for valid syntax (scheme and host).
4. **Privacy by convention, minimal offline checks**: `owner_team` is intended for team labels; policy validation rejects blank values and `@` (email addresses and `@handle` mentions), but cannot distinguish a person's name or username from a team label offline. Free-text fields like `reason` are stored as provided; contributors and users must avoid entering personal data.
5. **Deterministic gate results**: Given the same file, inventory, and `--today` date, the CLI produces identical exit codes (`0`, `1`, `2`) regardless of the local timezone.
6. **Locale-independent English CLI, bilingual documentation**: CLI messages, finding codes, and JSON payloads are intentionally kept in English regardless of OS locale (`LANG`/`LC_ALL`) so CI pipelines and automated log parsers behave identically across environments. User-facing documentation is maintained in both English (`README.md`) and Turkish (`README.tr.md`).

## Getting Started

### Prerequisites

- Python 3.11 or newer
- Git

### Setup Development Environment

```bash
# Clone and enter the repository
cd quarantine-ledger

# Create and activate a virtual environment
python -m venv .venv
# On Linux/macOS:
source .venv/bin/activate
# On Windows:
.venv\Scripts\activate

# Install pinned development tools and editable package (matches .github/workflows/ci.yml)
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.lock
python -m pip install -c requirements-dev.lock -e ".[dev]"

# Or install within compatible version bounds without lockfile constraints:
# python -m pip install -e ".[dev]"
```

## Running Checks Locally

We maintain a strict quality gate in `scripts/check.sh`:

```bash
bash scripts/check.sh
```

This single command executes:
1. File discovery check (verifying tools don't silently skip files).
2. Code linting with [Ruff](https://astral.sh/ruff).
3. Code formatting check with Ruff.
4. Static type analysis in strict mode with [Mypy](https://mypy-lang.org/).
5. Test suite with branch coverage enforcement (minimum 85%).

You can also run individual tools:

```bash
# Linting
ruff check src tests

# Formatting
ruff format src tests

# Type checking
mypy src/quarantine_ledger

# Tests with coverage
python -m pytest --cov=quarantine_ledger --cov-branch --cov-fail-under=85
```

## Testing Guidelines

- Every bug fix must include a regression test that fails before the fix and passes after.
- Keep test data synthetic and clear (e.g. `example.com`, fake team labels, synthetic dates).
- Cover error handling paths and boundary conditions (e.g. leap years, empty strings, missing inventory).

## Good First Issues

Looking for a place to start? The following starter issues are great for first-time contributors:

1. **Leap Year Examples & Edge Cases**: Expand synthetic examples and documentation demonstrating leap year calendar behavior (e.g., `2028-02-29`) under strict ISO validation.
2. **Team Breakdown Documentation**: Document recipes using `quarantine-ledger report --format json` with `jq` or small scripts to output team-by-team quarantine tables for CI summaries.
3. **Synthetic Test Runner Inventory Adapters**: Provide recipe snippets or example scripts in `examples/` that generate `tests.json` from popular runner collection outputs (`pytest --collect-only -q`, `jest --listTests --json`, or `go test -list`).

## Commit and Pull Request Guidelines

- Use clear and concise commit messages, preferably following the Conventional Commits specification (e.g., `fix: ...`, `feat: ...`, `docs: ...`, `test: ...`).
- Ensure `bash scripts/check.sh` passes completely before submitting a pull request.
- Ensure any new behavior is reflected in both `README.md` and `README.tr.md`.
- Keep changes focused: small, coherent pull requests are reviewed and merged much faster.
