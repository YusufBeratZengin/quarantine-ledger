"""CLI for quarantine ledger."""

import argparse
import json
import os
import sys
from datetime import date
from pathlib import Path

from . import __version__
from .dates import parse_date, today_utc
from .policy import check_ledger
from .reader import TomlParseError, ValidationError, load_inventory, parse_quarantine_toml

DEMO_QUARANTINE_TOML = """\
# Example quarantine ledger
# See https://github.com/YusufBeratZengin/quarantine-ledger

[policy]
max_age_days = 30
max_entries_per_team = 5
max_total_entries = 20

[[entries]]
id = "test_login_timeout"
owner_team = "auth-team"
issue = "https://github.com/example/project/issues/123"
reason = "Flaky due to network timing in CI"
created = "2026-10-01"
expires = "2026-11-01"

[[entries]]
id = "test_payment_retry"
owner_team = "payments-team"
issue = "https://github.com/example/project/issues/456"
reason = "Intermittent failure on staging environment"
created = "2026-10-15"
expires = "2026-11-15"

[[entries]]
id = "test_expired_example"
owner_team = "legacy-team"
issue = "https://github.com/example/project/issues/789"
reason = "This entry is expired to demonstrate expiry detection"
created = "2026-09-01"
expires = "2026-10-01"
"""

DEMO_TESTS_JSON = """\
[
  "test_login_timeout",
  "test_payment_retry",
  "test_user_registration",
  "test_password_reset"
]
"""

DEMO_README = """\
# Quarantine Ledger Demo

Run the check:

```bash
quarantine-ledger check quarantine.toml --inventory tests.json --today 2026-11-02
```

Expected: exit code 1, with five findings.

- `EXPIRED` for `test_login_timeout` (expires 2026-11-01, i.e. already past on
  2026-11-02) and for `test_expired_example` (2026-10-01).
- `MAX_AGE_EXCEEDED` for both, because `max_age_days = 30` and they were created
  32 and 62 days before the check date.
- `MISSING_FROM_INVENTORY` for `test_expired_example`: it stands in for a test
  that has been renamed or deleted, so it is absent from `tests.json`.

Without `--inventory` the last finding is not produced - "the test is gone" is
never inferred from the ledger alone.
"""

DEMO_FILES: dict[str, str] = {
    "quarantine.toml": DEMO_QUARANTINE_TOML,
    "tests.json": DEMO_TESTS_JSON,
    "README.md": DEMO_README,
}


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="quarantine-ledger",
        description="Check quarantined tests for expired, orphaned, or over-budget entries.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # check command
    check_parser = subparsers.add_parser("check", help="Check a quarantine ledger")
    check_parser.add_argument("ledger", type=Path, help="Path to quarantine.toml")
    check_parser.add_argument(
        "--inventory", type=Path, help="Path to test inventory JSON (list of test IDs)"
    )
    check_parser.add_argument(
        "--today", type=str, help="Override today's date (YYYY-MM-DD), default: UTC today"
    )
    check_parser.add_argument(
        "--format", choices=["text", "json"], default="text", help="Output format"
    )

    # report command
    report_parser = subparsers.add_parser(
        "report", help="Generate a report from a quarantine ledger"
    )
    report_parser.add_argument("ledger", type=Path, help="Path to quarantine.toml")
    report_parser.add_argument("--inventory", type=Path, help="Path to test inventory JSON")
    report_parser.add_argument("--today", type=str, help="Override today's date (YYYY-MM-DD)")
    report_parser.add_argument(
        "--format", choices=["json", "summary"], default="json", help="Output format"
    )

    # demo command
    demo_parser = subparsers.add_parser("demo", help="Create a demo project")
    demo_parser.add_argument("--dir", type=Path, default=Path("demo"), help="Demo directory")

    return parser


def _resolve_today(value: str | None) -> date:
    """Resolve --today, raising ValueError on a malformed date.

    An omitted option (None) means UTC today; an explicitly supplied empty
    string is an invalid value, not the default.
    """
    return today_utc() if value is None else parse_date(value)


def run_check(args: argparse.Namespace) -> int:
    """Run the check command."""
    try:
        ledger = parse_quarantine_toml(args.ledger)
    except (TomlParseError, ValidationError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 2

    try:
        today = _resolve_today(args.today)
    except ValueError as e:
        print(f"Error: invalid --today: {e}", file=sys.stderr)
        return 2

    inventory = None
    if args.inventory:
        try:
            inventory = load_inventory(args.inventory)
        except (TomlParseError, ValidationError) as e:
            print(f"Error: Failed to load inventory: {e}", file=sys.stderr)
            return 2

    result = check_ledger(ledger, today, inventory)

    if args.format == "json":
        output = {
            "exit_code": result.exit_code,
            "checked_entries": result.checked_entries,
            "inventory_provided": result.inventory_provided,
            "findings": [
                {
                    "code": f.code,
                    "message": f.message,
                    "entry_id": f.entry_id,
                    "entry_index": f.entry_index,
                    "team": f.team,
                }
                for f in result.findings
            ],
        }
        print(json.dumps(output, indent=2))
    else:
        if result.has_errors:
            print(f"FAIL: {len(result.findings)} finding(s)")
            for f in result.findings:
                loc = f" [{f.entry_id}]" if f.entry_id else (f" [team:{f.team}]" if f.team else "")
                print(f"  {f.code}{loc}: {f.message}")
        else:
            print(f"OK: {result.checked_entries} entry(ies) checked, no findings")

    return result.exit_code


def run_report(args: argparse.Namespace) -> int:
    """Run the report command."""
    try:
        ledger = parse_quarantine_toml(args.ledger)
    except (TomlParseError, ValidationError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 2

    try:
        today = _resolve_today(args.today)
    except ValueError as e:
        print(f"Error: invalid --today: {e}", file=sys.stderr)
        return 2

    inventory = None
    if args.inventory:
        try:
            inventory = load_inventory(args.inventory)
        except (TomlParseError, ValidationError) as e:
            print(f"Error: Failed to load inventory: {e}", file=sys.stderr)
            return 2

    result = check_ledger(ledger, today, inventory)

    by_code: dict[str, int] = {}
    for f in result.findings:
        by_code[f.code] = by_code.get(f.code, 0) + 1

    if args.format == "json":
        output = {
            "policy": {
                "max_age_days": ledger.policy.max_age_days,
                "max_entries_per_team": ledger.policy.max_entries_per_team,
                "max_total_entries": ledger.policy.max_total_entries,
            },
            "summary": {
                "total_entries": ledger.entry_count,
                "checked_entries": result.checked_entries,
                "inventory_provided": result.inventory_provided,
                "findings_count": len(result.findings),
                "by_code": by_code,
            },
            "entries": [
                {
                    "id": e.id,
                    "owner_team": e.owner_team,
                    "issue": e.issue,
                    "reason": e.reason,
                    "created": e.created.isoformat(),
                    "expires": e.expires.isoformat(),
                    "expired": e.expires <= today,
                    "age_days": (today - e.created).days,
                }
                for e in ledger.entries
            ],
            "findings": [
                {
                    "code": f.code,
                    "message": f.message,
                    "entry_id": f.entry_id,
                    "entry_index": f.entry_index,
                    "team": f.team,
                }
                for f in result.findings
            ],
        }
        print(json.dumps(output, indent=2))
    else:
        # Summary format
        print("Quarantine Ledger Report")
        print("=========================")
        print(f"Total entries: {ledger.entry_count}")
        print(
            f"Policy: max_age_days={ledger.policy.max_age_days}, "
            f"max_per_team={ledger.policy.max_entries_per_team}, "
            f"max_total={ledger.policy.max_total_entries}"
        )
        print(
            f"Checked: {result.checked_entries}, "
            f"Inventory: {'yes' if result.inventory_provided else 'no'}"
        )
        print(f"Findings: {len(result.findings)}")
        if result.findings:
            for code, count in sorted(by_code.items()):
                print(f"  {code}: {count}")

    return 0


def _demo_target_and_temp_names() -> list[str]:
    """Return both destination file names and their staging temporary file names."""
    names: list[str] = []
    for name in DEMO_FILES:
        names.append(name)
        names.append(f".{name}.tmp")
    return names


def run_demo(args: argparse.Namespace) -> int:
    """Write the demo files, refusing to replace anything that already exists."""
    demo_dir: Path = args.dir

    if demo_dir.exists() and not demo_dir.is_dir():
        return _fail(f"'{demo_dir}' exists and is not a directory")

    conflicts = sorted(name for name in _demo_target_and_temp_names() if (demo_dir / name).exists())
    if conflicts:
        joined = ", ".join(conflicts)
        return _fail(
            f"refusing to overwrite existing file(s) in '{demo_dir}': {joined}; pass an empty --dir"
        )

    created_dir = not demo_dir.exists()
    try:
        demo_dir.mkdir(parents=True, exist_ok=True)
        _write_demo_files(demo_dir, created_dir)
    except OSError as exc:
        return _fail(
            f"could not create demo in '{demo_dir}': {exc}; "
            "any partially written demo files were removed"
        )

    print(f"Demo created in {demo_dir}")
    print(
        f"Run: quarantine-ledger check {demo_dir / 'quarantine.toml'} "
        f"--inventory {demo_dir / 'tests.json'} --today 2026-11-02"
    )
    return 0


def _move_without_overwrite(source: Path, target: Path) -> None:
    """Atomically move source to target without overwriting an existing target.

    Raises FileExistsError (an OSError subclass) if target already exists.
    """
    try:
        target.hardlink_to(source)
        source.unlink()
    except OSError as exc:
        if isinstance(exc, FileExistsError):
            raise
        if os.name == "nt":
            source.rename(target)
            return
        raise


def _write_demo_files(demo_dir: Path, created_dir: bool) -> None:
    """Write every demo file, or leave nothing behind on failure.

    Each file is written to an exclusive temporary name and moved into place
    using an atomic non-overwriting operation, so an interrupted write never
    leaves a truncated ``quarantine.toml``, pre-existing temp files are never
    overwritten, and any race condition creating the target file during staging
    is rejected with FileExistsError without overwriting the target. If any step
    fails, the files produced by this call are deleted and a directory that this
    call created is removed again.
    """
    written: list[Path] = []
    try:
        for name, content in DEMO_FILES.items():
            target = demo_dir / name
            temp = demo_dir / f".{name}.tmp"
            temp_created = False
            try:
                with temp.open("x", encoding="utf-8", newline="\n") as f:
                    temp_created = True
                    f.write(content)
                _move_without_overwrite(temp, target)
            finally:
                if temp_created and temp.exists():
                    try:
                        temp.unlink()
                    except OSError:  # pragma: no cover - race condition / already replaced
                        pass
            written.append(target)
    except OSError:
        _remove_partial_demo(demo_dir, written, created_dir)
        raise


def _remove_partial_demo(demo_dir: Path, written: list[Path], created_dir: bool) -> None:
    """Best-effort rollback of a failed ``demo`` run."""
    for path in written:
        try:
            path.unlink(missing_ok=True)
        except OSError:  # pragma: no cover - nothing useful left to do
            pass
    if created_dir:
        try:
            demo_dir.rmdir()
        except OSError:  # pragma: no cover - directory not empty or gone
            pass


def _fail(message: str) -> int:
    print(f"Error: {message}", file=sys.stderr)
    return 2


def main(argv: list[str] | None = None) -> int:
    parser = create_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as e:
        # Preserve argparse's successful --help/--version exit contract.
        if e.code == 0:
            raise
        code = e.code
        return code if isinstance(code, int) else 0

    if args.command == "check":
        return run_check(args)
    elif args.command == "report":
        return run_report(args)
    elif args.command == "demo":
        return run_demo(args)
    else:
        parser.print_help()
        return 2


if __name__ == "__main__":
    sys.exit(main())
