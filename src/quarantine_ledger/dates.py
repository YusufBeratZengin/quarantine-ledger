"""Date parsing and handling for quarantine ledger."""

import re
from datetime import UTC, date, datetime

_STRICT_DATE_REGEX = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def parse_date(value: str) -> date:
    """Parse a date string in strict YYYY-MM-DD format."""
    if not isinstance(value, str) or not _STRICT_DATE_REGEX.match(value):
        raise ValueError(f"Invalid date format '{value}': expected YYYY-MM-DD")
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as e:
        raise ValueError(f"Invalid date format '{value}': expected YYYY-MM-DD") from e


def parse_optional_date(value: str | None) -> date | None:
    """Parse an optional date string."""
    if value is None or value == "":
        return None
    return parse_date(value)


def format_date(d: date) -> str:
    """Format a date as YYYY-MM-DD."""
    return d.strftime("%Y-%m-%d")


def today_utc() -> date:
    """Get today's date in UTC."""
    return datetime.now(UTC).date()


def days_between(start: date, end: date) -> int:
    """Calculate days between two dates (end - start)."""
    return (end - start).days


def is_expired(expires: date, today: date) -> bool:
    """Check if a date is expired (<= today)."""
    return expires <= today
