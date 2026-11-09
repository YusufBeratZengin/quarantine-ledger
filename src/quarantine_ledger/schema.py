"""Schema definitions and the shared field rules for quarantine ledger entries.

The ``*_problem`` helpers below are the single source of truth for field
syntax. Both ``QuarantineEntry.validate_*`` (library-side input validation) and
``policy`` (the CLI's finding pass) call them, so a rule cannot drift between
the two paths.
"""

import re
from dataclasses import dataclass
from datetime import date
from urllib.parse import urlsplit

from .dates import is_expired

# Exact test ids only: alphanumerics plus '.', '_', '-', '/' within segments,
# with optional '::' separators between segments as used by test runners' node
# ids (``tests/test_auth.py::TestLogin::test_timeout``). Single ':' or malformed
# colon runs and glob wildcards are rejected so rules match the documented syntax
# and cannot create broad, unreviewable exemptions.
ID_PATTERN = re.compile(r"^[a-zA-Z0-9._/-]+(?:::[a-zA-Z0-9._/-]+)*$")
ID_ALLOWED_HINT = "alphanumeric, '.', '_', '-', '/' and '::'"


def id_problem(value: str) -> str | None:
    """Explain why ``value`` is not an exact test id, or return None if it is."""
    if not value:
        return "empty"
    if "*" in value or "?" in value:
        return f"wildcards are not allowed in '{value}'; list the exact test id"
    if not ID_PATTERN.fullmatch(value) or not any(char.isalnum() for char in value):
        return f"invalid characters in '{value}' (allowed: {ID_ALLOWED_HINT})"
    return None


def owner_team_problem(value: str) -> str | None:
    """Check basic ``owner_team`` syntax, or return None if acceptable.

    This offline check only requires a non-blank string and rejects values
    containing '@' (such as email addresses or '@handle' mentions). Without an
    organization directory it cannot distinguish a person's name or username
    from a team label; maintainers must enforce team naming conventions by
    review and avoid entering personal data into ledgers.
    """
    if not value or not value.strip():
        return "empty"
    if "@" in value:
        return f"looks like an email '{value}', use a team name"
    return None


def issue_problem(value: str) -> str | None:
    """Offline syntax check for an issue URL: http(s) scheme and a host.

    Reachability is deliberately not checked - this is a syntax gate, not a
    network probe.
    """
    if not value:
        return "empty"
    if any(char.isspace() for char in value):
        return f"must not contain whitespace, got '{value}'"
    if not value.startswith(("http://", "https://")):
        return f"must be a URL starting with http or https, got '{value}'"
    try:
        parts = urlsplit(value)
        _ = parts.port  # rejects a non-numeric or out-of-range port
    except ValueError:
        return f"malformed URL '{value}'"
    if not parts.hostname:
        return f"must include a host, e.g. https://github.com/owner/repo/issues/1 (got '{value}')"
    return None


def reason_problem(value: str) -> str | None:
    """Explain why ``value`` is not a usable justification, or return None."""
    if not value or not value.strip():
        return "empty or whitespace only"
    return None


@dataclass(frozen=True)
class QuarantineEntry:
    """A single quarantined test entry."""

    id: str
    owner_team: str
    issue: str
    reason: str
    created: date
    expires: date

    def validate_id_format(self) -> list[str]:
        """Validate ID format - exact match only, no wildcards."""
        problem = id_problem(self.id)
        return [] if problem is None else [f"id: {problem}"]

    def validate_owner_team(self) -> list[str]:
        """Validate owner_team syntax (non-blank and no '@' email/handle)."""
        problem = owner_team_problem(self.owner_team)
        return [] if problem is None else [f"owner_team: {problem}"]

    def validate_issue(self) -> list[str]:
        """Validate issue URL - offline syntax check only."""
        problem = issue_problem(self.issue)
        return [] if problem is None else [f"issue: {problem}"]

    def validate_reason(self) -> list[str]:
        """Validate reason - non-empty justification."""
        problem = reason_problem(self.reason)
        return [] if problem is None else [f"reason: {problem}"]

    def validate_dates(self, today: date, max_age_days: int | None = None) -> list[str]:
        """Validate created/expires dates against today and max age policy."""
        errors = []
        if self.created > self.expires:
            errors.append(f"dates: created {self.created} > expires {self.expires}")
        if is_expired(self.expires, today):
            errors.append(f"expires: {self.expires} <= today {today} (expired or expires today)")
        if max_age_days is not None:
            age = (today - self.created).days
            if age > max_age_days:
                errors.append(f"max_age: entry age {age} days > policy max {max_age_days} days")
        return errors

    def validate_all(self, today: date, max_age_days: int | None = None) -> list[str]:
        """Run all validations."""
        errors = []
        errors.extend(self.validate_id_format())
        errors.extend(self.validate_owner_team())
        errors.extend(self.validate_issue())
        errors.extend(self.validate_reason())
        errors.extend(self.validate_dates(today, max_age_days))
        return errors


@dataclass(frozen=True)
class Policy:
    """Policy configuration for quarantine ledger."""

    max_age_days: int | None = None
    max_entries_per_team: int | None = None
    max_total_entries: int | None = None

    def validate(self) -> list[str]:
        """Validate policy values."""
        errors = []
        if self.max_age_days is not None and self.max_age_days <= 0:
            errors.append("max_age_days: must be positive")
        if self.max_entries_per_team is not None and self.max_entries_per_team <= 0:
            errors.append("max_entries_per_team: must be positive")
        if self.max_total_entries is not None and self.max_total_entries <= 0:
            errors.append("max_total_entries: must be positive")
        return errors


@dataclass(frozen=True)
class Ledger:
    """Complete quarantine ledger with entries and policy."""

    entries: tuple[QuarantineEntry, ...]
    policy: Policy

    @property
    def entry_count(self) -> int:
        return len(self.entries)

    def get_entries_by_team(self, team: str) -> tuple[QuarantineEntry, ...]:
        return tuple(e for e in self.entries if e.owner_team == team)

    def get_duplicate_ids(self) -> dict[str, list[QuarantineEntry]]:
        """Find duplicate IDs, returning dict of id -> list of entries."""
        seen: dict[str, list[QuarantineEntry]] = {}
        for entry in self.entries:
            seen.setdefault(entry.id, []).append(entry)
        return {k: v for k, v in seen.items() if len(v) > 1}
