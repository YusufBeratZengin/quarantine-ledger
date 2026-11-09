# Changelog

All notable changes to `quarantine-ledger` will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-11-07

### Added
- **Core policy and schema engine**:
  - `QuarantineEntry` schema enforcing `id`, `owner_team`, `issue`, `reason`, `created`, and `expires`.
  - `Policy` rules supporting `max_age_days`, `max_entries_per_team`, and `max_total_entries`.
  - Offline URL syntax validation for issue tracking references (scheme and host required; no network calls).
  - Validation rejecting wildcard characters in test IDs (`*`, `?`) to prevent blanket exemptions.
- **CLI interface**:
  - `quarantine-ledger check`: Gate validation with deterministic exit codes (`0` clean, `1` broken gate / expired / missing test, `2` validation or policy errors).
  - `quarantine-ledger report`: Detailed human-readable summary and structured JSON output for CI pipeline ingestion.
  - `quarantine-ledger demo`: Generates sample quarantine files and inventory with atomic staging and overwrite protection.
- **Strict date parsing**:
  - Exact `YYYY-MM-DD` calendar validation in UTC, preventing timezone drift around midnight.
  - Explicit rejection of unpadded date strings (e.g. `2026-1-2`).
- **Inventory verification**:
  - Cross-referencing against test runner JSON inventories to catch orphaned quarantine entries when tests are deleted or renamed.
- **Developer & CI infrastructure**:
  - Zero runtime dependencies; uses Python 3.11+ standard library (`tomllib`, `argparse`, `datetime`, `urllib.parse`).
  - Comprehensive test suite with >97% branch coverage.
  - Local quality gate script (`scripts/check.sh`) verifying discovery, ruff lint, ruff format, mypy strict mode, and pytest coverage.
  - GitHub Actions matrix CI for Linux and Windows across Python 3.11 and 3.13.
  - Complete pre-release documentation, including English `README.md`, Turkish `README.tr.md`, `CONTRIBUTING.md`, `SECURITY.md`, and `CODE_OF_CONDUCT.md`.

### Fixed
- Tighten `ID_PATTERN` in `schema.py` so only `::` segment separators are accepted and single or malformed colons (`:`, `:::`) are rejected as `INVALID_ID`, matching the documented rule.
- Clarify offline `owner_team` privacy boundaries across `SECURITY.md`, `README.md`, `README.tr.md`, `CONTRIBUTING.md`, and `schema.py` docstrings (syntax checks reject blank values and `@`, while distinguishing team labels from personal names remains a maintainer convention).
- Document exit-code precedence on mixed findings (`1` takes precedence over `2` once policy evaluation runs) and add regression coverage for expired entries combined with budget violations.
- Convert invalid UTF-8 byte sequences (`UnicodeDecodeError`) in `--inventory` JSON and `quarantine.toml` inputs into clean user-facing input errors (exit code `2`, no traceback).
- Align `.github/workflows/ci.yml` with `requirements-dev.lock` (including complete transitive pins) for reproducible CI installations.
- Prevent race condition file overwrites in `demo`: use atomic non-overwriting moves (`_move_without_overwrite`) to guarantee target files created during staging are never overwritten.
- Enforce whitespace rejection in `owner_team` validation across both schema and policy checks.
- Enforce strict `YYYY-MM-DD` date regex before `strptime` parsing to reject unpadded dates such as `2026-1-2`.
- Pre-check both target and `.tmp` file paths in `demo` command and use exclusive file creation (`open(..., "x")`) to prevent truncating or deleting pre-existing temporary files.
- Reject unrecognized root TOML keys so typos like `[[entry]]` fail loudly instead of creating a silently empty ledger.
- Ensure atomic rollback on demo generation failures, unlinking only files created during the active run.
