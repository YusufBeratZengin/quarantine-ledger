# quarantine-ledger

Put owners, deadlines and budgets on quarantined tests.

`quarantine-ledger` is a small, dependency-free CLI that reads a hand-written
quarantine file and fails your quality gate when an exemption has expired, lost
its owner, points at a missing issue, duplicates another entry, or exceeds the
budget your team agreed on. It never changes test results: it does not skip,
`xfail` or delete anything, and it never talks to the network.

- English documentation: this file
- Türkçe belge: [README.tr.md](README.tr.md)

## Install

Python 3.11 or newer. There are no runtime dependencies.

```bash
python -m pip install .
```

For development (tests, lint, types; add `-c requirements-dev.lock` for exact CI tool versions):

```bash
python -m pip install -c requirements-dev.lock -e ".[dev]"
```

## 30-second example

```bash
quarantine-ledger --version
quarantine-ledger demo --dir demo-out
quarantine-ledger check demo-out/quarantine.toml --inventory demo-out/tests.json --today 2026-11-02
```

Real output (Windows, Python 3.14; the paths are the only OS-specific part).
CLI output, finding codes, and JSON payloads are intentionally English-only and
locale-independent (`LANG`/`LC_ALL` are ignored) so CI pipelines can parse them
deterministically, while documentation is provided in both English (`README.md`)
and Turkish (`README.tr.md`):

```text
Demo created in demo-out
Run: quarantine-ledger check demo-out\quarantine.toml --inventory demo-out\tests.json --today 2026-11-02

FAIL: 5 finding(s)
  EXPIRED [test_login_timeout]: Entry 'test_login_timeout': expires 2026-11-01 <= today 2026-11-02
  MAX_AGE_EXCEEDED [test_login_timeout]: Entry 'test_login_timeout': age 32 days > max_age_days 30
  EXPIRED [test_expired_example]: Entry 'test_expired_example': expires 2026-10-01 <= today 2026-11-02
  MAX_AGE_EXCEEDED [test_expired_example]: Entry 'test_expired_example': age 62 days > max_age_days 30
  MISSING_FROM_INVENTORY [test_expired_example]: Test 'test_expired_example' not found in inventory (it may have been renamed or deleted)
```

Exit code: `1`.

`demo` refuses to overwrite anything that already exists. It checks both the target
file names and temporary staging files (e.g., `.quarantine.toml.tmp`), creating each
file exclusively so existing files are never truncated or unlinked. A second run is
a clean usage error:

```text
Error: refusing to overwrite existing file(s) in 'demo-out': README.md, quarantine.toml, tests.json; pass an empty --dir
```

Exit code: `2`.

## The quarantine file

```toml
[policy]
max_age_days = 30          # optional: reject entries older than this
max_entries_per_team = 5   # optional: per owner_team budget
max_total_entries = 20     # optional: whole-ledger budget

[[entries]]
id = "test_login_timeout"                                   # exact test id, no wildcards
owner_team = "auth-team"                                    # intended for a team label; '@' is rejected
issue = "https://github.com/example/project/issues/123"     # http(s) URL, syntax-checked offline
reason = "Flaky due to network timing in CI"                # must not be empty
created = "2026-10-01"                                      # YYYY-MM-DD
expires = "2026-11-01"                                      # YYYY-MM-DD
```

Rules enforced while reading the file (any violation is a validation error and
exit code `2`, with every problem listed, not just the first one):

- both `quarantine.toml` and any `--inventory` JSON file must be valid UTF-8.
  Unreadable files or invalid UTF-8 byte sequences (such as UTF-16 output) fail
  cleanly with exit code `2` and an error message instead of a traceback.
- only two top-level keys exist: `entries` and `policy`. Any other root key is
  an error, so the `[[entry]]` (singular) typo cannot turn a ledger into a
  silently empty one that passes with "0 entries checked". A completely empty
  file is an error for the same reason. A file with just a `[policy]` table is
  still a valid empty quarantine list.
- `policy` must be a table; only `max_age_days`, `max_entries_per_team` and
  `max_total_entries` are accepted, all positive integers (`true`/`false` and
  quoted numbers are rejected instead of being coerced).
- every entry must be a table with exactly the six keys above; unknown keys and
  non-string values are reported, so a typo like `expires_at` fails loudly
  instead of silently meaning "no deadline".
- `created` and `expires` must be strict zero-padded `YYYY-MM-DD` strings (e.g.
  `2026-01-02`). Non-padded dates like `2026-1-2` or malformed strings are
  usage errors, never silently accepted or skipped.

Field *content* rules run in `check`, so they show up as findings next to expiry
and budget problems (still exit code `2`, still all reported at once):

- `id` must be an exact test id: alphanumerics plus `.`, `_`, `-`, `/` within
  segments, with optional `::` separators between segments. Runner node ids such
  as `tests/test_auth.py::TestLogin::test_timeout` are accepted as-is, while
  single colons (`test:login`), malformed colon runs (`:::`), and wildcards
  (`test_*`) are rejected with `INVALID_ID` - a glob would exempt a whole family
  of tests.
- `owner_team` must be non-blank and must not contain `@` (rejecting email
  addresses and `@handle` mentions with `OWNER_TEAM_LOOKS_LIKE_EMAIL`). Offline
  syntax checks cannot distinguish a person's name or username from a team
  label, so using team names rather than personal names remains a review
  convention.
- `issue` must be an `http://` or `https://` URL that names a host. `https://`
  alone is rejected with `INVALID_ISSUE_URL`. Only the syntax is checked; the
  URL is never fetched, so no accessibility is claimed.

## What `check` reports

| Code | Meaning | Exit |
| --- | --- | --- |
| `EXPIRED` | `expires <= today` (the day it expires counts as expired) | 1 |
| `MISSING_FROM_INVENTORY` | entry id is not in `--inventory` (test renamed/deleted) | 1 |
| `INVALID_DATE` | `created` is after `expires` | 1 |
| `DUPLICATE_ID` | the same id appears more than once (one finding per row) | 2 |
| `MAX_AGE_EXCEEDED` | entry is older than `policy.max_age_days` | 2 |
| `BUDGET_EXCEEDED_TOTAL` | more entries than `policy.max_total_entries` | 2 |
| `BUDGET_EXCEEDED_TEAM` | a team holds more than `policy.max_entries_per_team` | 2 |
| `EMPTY_ID`, `EMPTY_OWNER_TEAM`, `EMPTY_ISSUE`, `EMPTY_REASON` | required field is missing/blank | 2 |
| `OWNER_TEAM_LOOKS_LIKE_EMAIL` | `owner_team` contains `@`; use a team label | 2 |
| `INVALID_ID` | id is not an exact test id (wildcard or unsupported character) | 2 |
| `INVALID_ISSUE_URL` | issue is not an `http(s)://` URL with a host, e.g. `https://` | 2 |

### Exit codes

`check` serves as a quality gate command; its exit code reflects whether the ledger passes policy:

| Code | Meaning |
| --- | --- |
| `0` | no findings (quality gate passes) |
| `1` | the gate is broken now (expired, missing test, impossible dates) |
| `2` | usage/input error, or ledger-level policy violations (duplicates, budgets, bad ids, empty fields, bad URL) |

**Precedence on mixed findings:** Input/usage errors (unreadable or non-UTF-8
files, invalid TOML/JSON, schema type errors, bad `--today`) abort before policy
evaluation with exit code `2`. Once policy checks run, every finding is reported
together; if both gate-breaking findings (`1`: `EXPIRED`,
`MISSING_FROM_INVENTORY`, `INVALID_DATE`) and ledger-policy findings (`2`: e.g.
`BUDGET_EXCEEDED_*`, `MAX_AGE_EXCEEDED`, `DUPLICATE_ID`, `INVALID_*`, `EMPTY_*`,
`OWNER_TEAM_LOOKS_LIKE_EMAIL`) occur in the same run, exit code `1` takes
precedence so an actively broken quality gate is never masked as a
configuration-only issue.

An `--inventory`-less run never reports `MISSING_FROM_INVENTORY`: "the test no
longer exists" cannot be inferred from the ledger alone.

`report` is an inspection and reporting tool rather than a quality gate: it exits with `0` as long as report generation succeeds, even when findings or expired entries are present (allowing CI to collect and publish report artifacts without prematurely failing the pipeline). It exits with `2` only on usage or file input errors.

## Report

```bash
quarantine-ledger report quarantine.toml --format summary
quarantine-ledger report quarantine.toml --format json > quarantine-report.json
```

`json` contains `policy`, `summary` (including `by_code`), one object per entry
(with `expired` and `age_days` computed against `--today`) and the `findings`
array. Note that `report` exits `0` on successful report emission regardless of
findings; use `check` when an exit code is needed to fail CI. `check --format json`
emits `exit_code`, `checked_entries`, `inventory_provided` and `findings`.

## Using it in CI

```yaml
- name: Quarantine ledger
  run: |
    python -m pip install quarantine-ledger
    quarantine-ledger check quarantine.toml --inventory tests.json --today "$(date -u +%F)"
```

Pass a fixed `--today` in tests and let CI supply the real UTC date in
production; that keeps results deterministic and avoids local-timezone drift
around midnight.

## Development

```bash
bash scripts/check.sh
```

The script runs ruff (lint + format), mypy in strict mode and pytest with branch
coverage (`--cov-fail-under=85`) from the project root, whatever the current
directory is. It also verifies that ruff actually discovered Python files before
claiming success: this project once sat inside a parent repository whose
`.git/info/exclude` was `*`, which made ruff skip every file while still exiting
`0`. Ruff is therefore invoked with `--no-respect-gitignore` (set
`QUARANTINE_LEDGER_RESPECT_GITIGNORE=1` to restore the default).

- `src/quarantine_ledger/schema.py` - entry/policy dataclasses and their rules
- `src/quarantine_ledger/reader.py` - TOML/JSON loading and full validation
- `src/quarantine_ledger/policy.py` - the checks, findings and exit-code mapping
- `src/quarantine_ledger/dates.py` - strict `YYYY-MM-DD` parsing, UTC "today"
- `src/quarantine_ledger/cli.py` - argparse front end, text/JSON output, `demo`
- `examples/` - the same sample ledger shipped as static files
- `.github/workflows/ci.yml` - Linux and Windows, Python 3.11 and 3.13
- [CHANGELOG.md](CHANGELOG.md) - version history and release notes
- [CONTRIBUTING.md](CONTRIBUTING.md) - developer setup and guidelines
- [SECURITY.md](SECURITY.md) - vulnerability reporting and security guarantees
- [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) - community participation standards

## Scope and honest limits

- Static check of a file you maintain by hand. No flaky-test detection, no
  automatic `skip`/`xfail`, no test deletion, no issue creation, no notifications.
- Issue URLs are syntax-checked only (scheme plus a host); accessibility is
  never claimed. Nothing is sent over the network.
- Test ids must match exactly. Wildcards are rejected on purpose: a glob would
  turn one line into a blanket exemption.
- Inventory adapters for pytest markers, Jest and Playwright are not implemented
  yet; `--inventory` expects a JSON array of test-id strings, which any runner
  can produce in a few lines.
- The GitHub Actions CI matrix (`ubuntu-latest` + `windows-latest`, Python 3.11
  and 3.13) has not been executed on GitHub from this environment. Local
  verification covers `bash scripts/check.sh` on Windows (Python 3.14) and
  isolated wheel installation + CLI smoke checks on Python 3.11 and 3.14; verify
  the full GitHub Actions matrix on push before cutting a release.
- `owner_team` validation only checks that the value is non-blank and does not
  contain `@` (rejecting email addresses and `@handle` mentions). Because the
  tool runs offline without an organization directory, person names or usernames
  without `@` cannot be detected automatically, and free-text fields like
  `reason` are not scanned for personal data; maintainers should keep personal
  data out of ledgers.

## License

MIT, see [LICENSE](LICENSE).
