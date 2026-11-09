#!/usr/bin/env bash
# scripts/check.sh - full local quality gate: lint, format, types, tests.
# Exit 0 only if every step passes. Safe to run from any directory.

set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

# Ruff skips files that its gitignore support considers ignored. That silently
# turned this gate into a no-op once (the checkout sat inside a parent repository
# whose .git/info/exclude is "*"), so discovery is explicit and verified below.
# Set QUARANTINE_LEDGER_RESPECT_GITIGNORE=1 to restore ruff's default behaviour.
RUFF_FLAGS=()
if [[ "${QUARANTINE_LEDGER_RESPECT_GITIGNORE:-0}" != "1" ]]; then
    RUFF_FLAGS+=(--no-respect-gitignore)
fi

TARGETS=(src tests)

echo "=== Checking ruff file discovery ==="
mapfile -t PY_FILES < <(ruff check "${RUFF_FLAGS[@]}" --show-files "${TARGETS[@]}")
if [[ "${#PY_FILES[@]}" -eq 0 ]]; then
    echo "ERROR: ruff found no Python files under ${TARGETS[*]}" >&2
    echo "       Refusing to report a passing lint run that checked nothing." >&2
    exit 1
fi
echo "Linting ${#PY_FILES[@]} file(s)"

echo "=== Running lint (ruff) ==="
ruff check "${RUFF_FLAGS[@]}" "${TARGETS[@]}"

echo "=== Running format check (ruff) ==="
ruff format "${RUFF_FLAGS[@]}" --check "${TARGETS[@]}"

echo "=== Running type check (mypy) ==="
mypy src/quarantine_ledger

echo "=== Running tests with coverage ==="
python -m pytest --cov=quarantine_ledger --cov-branch --cov-fail-under=85

echo "=== All checks passed ==="
