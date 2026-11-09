"""Parsing and validation for quarantine ledger input files."""

import json
import tomllib
from datetime import date, datetime
from pathlib import Path
from typing import Any

from .dates import parse_date
from .schema import Ledger, Policy, QuarantineEntry

POLICY_KEYS: tuple[str, ...] = (
    "max_age_days",
    "max_entries_per_team",
    "max_total_entries",
)
ENTRY_STRING_KEYS: tuple[str, ...] = ("id", "owner_team", "issue", "reason")
ENTRY_DATE_KEYS: tuple[str, ...] = ("created", "expires")
ENTRY_KEYS: tuple[str, ...] = ENTRY_STRING_KEYS + ENTRY_DATE_KEYS
ROOT_KEYS: tuple[str, ...] = ("entries", "policy")


def _type_name(value: object) -> str:
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    return type(value).__name__


class TomlParseError(Exception):
    """Raised when a file cannot be read or parsed as TOML/JSON."""


class ValidationError(Exception):
    """Raised when a file is parseable but its contents are not a valid ledger."""

    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__("\n".join(errors))


def parse_quarantine_toml(path: Path) -> Ledger:
    """Parse a quarantine.toml file into a Ledger.

    Raises TomlParseError for I/O or syntax problems and ValidationError with the
    complete list of schema problems (wrong types, unknown keys - including
    top-level ones - and bad dates).
    """
    data = _load_toml(path)

    errors: list[str] = []
    _check_root_keys(data, errors)
    policy = _build_policy(data.get("policy", {}), errors)
    entries = _build_entries(data.get("entries", []), errors)
    if errors:
        raise ValidationError(errors)

    return Ledger(entries=entries, policy=policy)


def load_inventory(path: Path) -> set[str]:
    """Load a test inventory from a JSON array of test ID strings."""
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except UnicodeDecodeError as exc:
        raise TomlParseError(f"Failed to decode inventory file as UTF-8: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise TomlParseError(f"Failed to parse inventory JSON: {exc}") from exc
    except OSError as exc:
        raise TomlParseError(f"Failed to read inventory file: {exc}") from exc

    if not isinstance(data, list):
        raise ValidationError(["inventory: must be a list of test ID strings"])

    inventory: set[str] = set()
    for index, item in enumerate(data):
        if not isinstance(item, str):
            raise ValidationError([
                f"inventory[{index}]: must be a string, got {type(item).__name__}"
            ])
        if not item.strip():
            raise ValidationError([f"inventory[{index}]: empty test id"])
        inventory.add(item)

    return inventory


def _load_toml(path: Path) -> dict[str, Any]:
    try:
        with path.open("rb") as handle:
            return tomllib.load(handle)
    except UnicodeDecodeError as exc:
        raise TomlParseError(f"Failed to decode TOML file as UTF-8: {exc}") from exc
    except tomllib.TOMLDecodeError as exc:
        raise TomlParseError(f"Failed to parse TOML: {exc}") from exc
    except OSError as exc:
        raise TomlParseError(f"Failed to read file: {exc}") from exc


def _check_root_keys(data: dict[str, Any], errors: list[str]) -> None:
    """Reject unknown top-level keys instead of ignoring them.

    Without this, a ``[[entry]]`` typo silently produced an empty ledger that
    passed the quality gate with "0 entries checked". A policy-only file (an
    empty quarantine list) stays valid, while an entirely empty file does not.
    """
    if not data:
        errors.append(
            "root: file is empty; expected at least a [policy] table or [[entries]] entries"
        )
        return

    allowed = ", ".join(ROOT_KEYS)
    for key in sorted(data):
        if key in ROOT_KEYS:
            continue
        message = f"root: unknown key '{key}' (allowed: {allowed})"
        if key == "entry":
            message += "; the array of tables must be spelled [[entries]]"
        errors.append(message)


def _build_policy(raw: Any, errors: list[str]) -> Policy:
    """Validate the optional ``[policy]`` table, collecting every problem."""
    if not isinstance(raw, dict):
        errors.append(f"policy: must be a table, got {type(raw).__name__}")
        return Policy()

    for key in sorted(raw):
        if key not in POLICY_KEYS:
            allowed = ", ".join(POLICY_KEYS)
            errors.append(f"policy: unknown key '{key}' (allowed: {allowed})")

    policy = Policy(
        max_age_days=_int_field(raw, "max_age_days", errors),
        max_entries_per_team=_int_field(raw, "max_entries_per_team", errors),
        max_total_entries=_int_field(raw, "max_total_entries", errors),
    )
    errors.extend(f"policy: {message}" for message in policy.validate())
    return policy


def _int_field(raw: dict[str, Any], key: str, errors: list[str]) -> int | None:
    """Return a positive-int policy value, recording a type error otherwise.

    ``bool`` is rejected explicitly because it is a subclass of ``int`` in Python
    and ``max_age_days = true`` would otherwise silently mean "1 day".
    """
    if key not in raw:
        return None
    value = raw[key]
    if isinstance(value, bool) or not isinstance(value, int):
        errors.append(f"policy.{key}: must be an integer, got {_type_name(value)}")
        return None
    return int(value)


def _build_entries(raw: Any, errors: list[str]) -> tuple[QuarantineEntry, ...]:
    """Validate ``[[entries]]`` tables, collecting every problem."""
    if not isinstance(raw, list):
        errors.append(f"entries: must be a list of tables, got {type(raw).__name__}")
        return ()

    entries: list[QuarantineEntry] = []
    for index, item in enumerate(raw):
        location = f"entries[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{location}: must be a table")
            continue

        for key in sorted(item):
            if key not in ENTRY_KEYS:
                allowed = ", ".join(ENTRY_KEYS)
                errors.append(f"{location}: unknown key '{key}' (allowed: {allowed})")

        values: dict[str, str] = {}
        for key in ENTRY_STRING_KEYS:
            values[key] = _string_field(item, key, location, errors)
        created = _date_field(item, "created", location, errors)
        expires = _date_field(item, "expires", location, errors)
        if created is None or expires is None:
            continue

        entries.append(
            QuarantineEntry(
                id=values["id"],
                owner_team=values["owner_team"],
                issue=values["issue"],
                reason=values["reason"],
                created=created,
                expires=expires,
            )
        )

    return tuple(entries)


def _string_field(item: dict[str, Any], key: str, location: str, errors: list[str]) -> str:
    value = item.get(key, "")
    if not isinstance(value, str):
        errors.append(f"{location}.{key}: must be a string, got {_type_name(value)}")
        return ""
    return value


def _date_field(item: dict[str, Any], key: str, location: str, errors: list[str]) -> date | None:
    """Parse a required YYYY-MM-DD field, recording parse errors."""
    value = item.get(key, "")
    if isinstance(value, date) and not isinstance(value, datetime):
        errors.append(
            f"{location}.{key}: TOML local dates are not supported, "
            "use a quoted string in YYYY-MM-DD format"
        )
        return None
    if not isinstance(value, str):
        errors.append(f"{location}.{key}: must be a string, got {_type_name(value)}")
        return None
    if not value.strip():
        errors.append(f"{location}.{key}: missing, expected YYYY-MM-DD")
        return None
    try:
        return parse_date(value)
    except ValueError as exc:
        errors.append(f"{location}.{key}: {exc}")
        return None
