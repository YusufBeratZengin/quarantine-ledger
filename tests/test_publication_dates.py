"""Tests for dates module."""

from datetime import date

import pytest

from quarantine_ledger.dates import (
    days_between,
    format_date,
    is_expired,
    parse_date,
    parse_optional_date,
    today_utc,
)


class TestParseDate:
    def test_valid_date(self):
        assert parse_date("2026-11-02") == date(2026, 11, 2)
        assert parse_date("2026-01-01") == date(2026, 1, 1)
        assert parse_date("2026-12-31") == date(2026, 12, 31)

    def test_invalid_format(self):
        with pytest.raises(ValueError, match="Invalid date format"):
            parse_date("02-11-2026")
        with pytest.raises(ValueError, match="Invalid date format"):
            parse_date("2026/11/02")
        with pytest.raises(ValueError, match="Invalid date format"):
            parse_date("not-a-date")
        with pytest.raises(ValueError, match="Invalid date format"):
            parse_date("")

    @pytest.mark.parametrize(
        "unpadded",
        [
            "2026-1-2",
            "2026-01-2",
            "2026-1-02",
            "2026-11-2",
            "2026-1-20",
            "20260102",
            "+2026-01-02",
        ],
    )
    def test_unpadded_or_malformed_iso_rejected(self, unpadded):
        with pytest.raises(ValueError, match="Invalid date format"):
            parse_date(unpadded)

    def test_invalid_date_values(self):
        with pytest.raises(ValueError):
            parse_date("2026-13-01")
        with pytest.raises(ValueError):
            parse_date("2026-02-30")


class TestParseOptionalDate:
    def test_none(self):
        assert parse_optional_date(None) is None

    def test_empty_string(self):
        assert parse_optional_date("") is None

    def test_valid(self):
        assert parse_optional_date("2026-11-02") == date(2026, 11, 2)


class TestFormatDate:
    def test_format(self):
        assert format_date(date(2026, 11, 2)) == "2026-11-02"
        assert format_date(date(2026, 1, 1)) == "2026-01-01"


class TestTodayUtc:
    def test_returns_date(self):
        # Just verify it returns a date object
        result = today_utc()
        assert isinstance(result, date)


class TestDaysBetween:
    def test_positive(self):
        assert days_between(date(2026, 1, 1), date(2026, 1, 11)) == 10

    def test_zero(self):
        assert days_between(date(2026, 1, 1), date(2026, 1, 1)) == 0

    def test_negative(self):
        assert days_between(date(2026, 1, 11), date(2026, 1, 1)) == -10


class TestIsExpired:
    def test_expired_today(self):
        assert is_expired(date(2026, 11, 2), date(2026, 11, 2)) is True

    def test_expired_past(self):
        assert is_expired(date(2026, 11, 1), date(2026, 11, 2)) is True

    def test_not_expired_future(self):
        assert is_expired(date(2026, 11, 3), date(2026, 11, 2)) is False
