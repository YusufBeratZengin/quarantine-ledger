"""Policy checking for quarantine ledger entries."""

from dataclasses import dataclass
from datetime import date

from .dates import is_expired
from .inventory import InventoryChecker
from .schema import (
    Ledger,
    QuarantineEntry,
    id_problem,
    issue_problem,
    owner_team_problem,
    reason_problem,
)

# Codes that mean the quality gate is broken right now (exit code 1) rather than
# "the ledger is misconfigured" (exit code 2).
GATE_BREAKING_CODES = frozenset({"EXPIRED", "MISSING_FROM_INVENTORY", "INVALID_DATE"})


@dataclass(frozen=True)
class Finding:
    """A single policy finding."""

    code: str
    message: str
    entry_id: str | None = None
    team: str | None = None
    entry_index: int | None = None


@dataclass(frozen=True)
class CheckResult:
    """Result of a policy check."""

    findings: tuple[Finding, ...]
    checked_entries: int
    inventory_provided: bool

    @property
    def has_errors(self) -> bool:
        return len(self.findings) > 0

    @property
    def exit_code(self) -> int:
        if not self.has_errors:
            return 0
        if any(finding.code in GATE_BREAKING_CODES for finding in self.findings):
            return 1
        return 2


def check_ledger(
    ledger: Ledger,
    today: date,
    inventory: set[str] | None = None,
) -> CheckResult:
    """Run all policy checks on a ledger."""
    findings: list[Finding] = []

    findings.extend(_check_duplicates(ledger))
    for index, entry in enumerate(ledger.entries):
        findings.extend(_check_entry(entry, index, today, ledger.policy.max_age_days))
    findings.extend(_check_inventory(ledger, inventory))
    findings.extend(_check_budgets(ledger))

    return CheckResult(
        findings=tuple(_deduplicate(findings)),
        checked_entries=len(ledger.entries),
        inventory_provided=inventory is not None,
    )


def _check_duplicates(ledger: Ledger) -> list[Finding]:
    duplicates = ledger.get_duplicate_ids()
    if not duplicates:
        return []

    findings: list[Finding] = []
    for index, entry in enumerate(ledger.entries):
        if entry.id not in duplicates:
            continue
        count = len(duplicates[entry.id])
        findings.append(
            Finding(
                code="DUPLICATE_ID",
                message=f"Duplicate entry id '{entry.id}' appears {count} times",
                entry_id=entry.id,
                entry_index=index,
            )
        )
    return findings


def _check_inventory(ledger: Ledger, inventory: set[str] | None) -> list[Finding]:
    """Report ledger ids absent from the inventory.

    Without an inventory this check is skipped entirely: "the test is gone" can
    never be inferred from the ledger alone.
    """
    if inventory is None:
        return []

    checker = InventoryChecker(inventory)
    return [
        Finding(
            code="MISSING_FROM_INVENTORY",
            message=(
                f"Test '{entry.id}' not found in inventory (it may have been renamed or deleted)"
            ),
            entry_id=entry.id,
            entry_index=index,
        )
        for index, entry in enumerate(ledger.entries)
        if not checker.has_entry(entry.id)
    ]


def _check_budgets(ledger: Ledger) -> list[Finding]:
    policy = ledger.policy
    findings: list[Finding] = []

    if policy.max_total_entries is not None and ledger.entry_count > policy.max_total_entries:
        findings.append(
            Finding(
                code="BUDGET_EXCEEDED_TOTAL",
                message=(
                    f"Total quarantine entries ({ledger.entry_count}) exceed "
                    f"the budget ({policy.max_total_entries})"
                ),
            )
        )

    if policy.max_entries_per_team is not None:
        for team in dict.fromkeys(entry.owner_team for entry in ledger.entries):
            count = len(ledger.get_entries_by_team(team))
            if count > policy.max_entries_per_team:
                findings.append(
                    Finding(
                        code="BUDGET_EXCEEDED_TEAM",
                        message=(
                            f"Team '{team}' has {count} entries, which exceeds "
                            f"the budget ({policy.max_entries_per_team})"
                        ),
                        team=team,
                    )
                )

    return findings


def _check_entry(
    entry: QuarantineEntry,
    index: int,
    today: date,
    max_age_days: int | None,
) -> list[Finding]:
    """Check a single entry against every rule."""
    findings: list[Finding] = []

    def add(code: str, message: str) -> None:
        findings.append(Finding(code=code, message=message, entry_id=entry.id, entry_index=index))

    if entry.created > entry.expires:
        add(
            "INVALID_DATE",
            f"Entry '{entry.id}': created {entry.created} > expires {entry.expires}",
        )

    if is_expired(entry.expires, today):
        add("EXPIRED", f"Entry '{entry.id}': expires {entry.expires} <= today {today}")

    if max_age_days is not None:
        age = (today - entry.created).days
        if age > max_age_days:
            add(
                "MAX_AGE_EXCEEDED",
                f"Entry '{entry.id}': age {age} days > max_age_days {max_age_days}",
            )

    if not entry.id:
        findings.append(
            Finding(code="EMPTY_ID", message="Entry has an empty id", entry_index=index)
        )
    else:
        # Same rule the schema documents: exact ids only, no wildcards.
        id_error = id_problem(entry.id)
        if id_error is not None:
            add("INVALID_ID", f"Entry '{entry.id}': {id_error}")

    if not entry.owner_team or not entry.owner_team.strip():
        add("EMPTY_OWNER_TEAM", f"Entry '{entry.id}': empty owner_team")
    elif owner_team_problem(entry.owner_team) is not None:
        add(
            "OWNER_TEAM_LOOKS_LIKE_EMAIL",
            f"Entry '{entry.id}': owner_team '{entry.owner_team}' looks like an email; "
            "use a team name",
        )

    if not entry.issue:
        add("EMPTY_ISSUE", f"Entry '{entry.id}': empty issue")
    else:
        issue_error = issue_problem(entry.issue)
        if issue_error is not None:
            add("INVALID_ISSUE_URL", f"Entry '{entry.id}': issue {issue_error}")

    if reason_problem(entry.reason) is not None:
        add("EMPTY_REASON", f"Entry '{entry.id}': empty or whitespace-only reason")

    return findings


def _deduplicate(findings: list[Finding]) -> list[Finding]:
    """Drop byte-identical findings while keeping one row per ledger entry."""
    seen: set[tuple[str, str | None, str | None, int | None]] = set()
    unique: list[Finding] = []
    for finding in findings:
        key = (finding.code, finding.entry_id, finding.team, finding.entry_index)
        if key in seen:
            continue
        seen.add(key)
        unique.append(finding)
    return unique
