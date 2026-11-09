"""Tests for schema module."""

from datetime import date

from quarantine_ledger.schema import Ledger, Policy, QuarantineEntry


class TestQuarantineEntry:
    def test_valid_entry(self):
        entry = QuarantineEntry(
            id="test_example",
            owner_team="auth-team",
            issue="https://github.com/example/issues/123",
            reason="Flaky due to network timing",
            created=date(2026, 10, 1),
            expires=date(2026, 11, 1),
        )
        errors = entry.validate_all(date(2026, 10, 15))
        assert errors == []

    def test_empty_id(self):
        entry = QuarantineEntry(
            id="",
            owner_team="auth-team",
            issue="https://github.com/example/issues/123",
            reason="Reason",
            created=date(2026, 10, 1),
            expires=date(2026, 11, 1),
        )
        errors = entry.validate_id_format()
        assert "id: empty" in errors

    def test_invalid_id_characters(self):
        entry = QuarantineEntry(
            id="test example",  # space not allowed
            owner_team="auth-team",
            issue="https://github.com/example/issues/123",
            reason="Reason",
            created=date(2026, 10, 1),
            expires=date(2026, 11, 1),
        )
        errors = entry.validate_id_format()
        assert any("invalid characters" in e for e in errors)

    def test_id_with_trailing_line_ending_rejected(self):
        # `$` used to match before a trailing newline, so "test1\n" passed.
        for bad_id in ["test1\n", "test1\r\n"]:
            entry = QuarantineEntry(
                id=bad_id,
                owner_team="auth-team",
                issue="https://github.com/example/issues/123",
                reason="Reason",
                created=date(2026, 10, 1),
                expires=date(2026, 11, 1),
            )
            errors = entry.validate_id_format()
            assert any("invalid characters" in e for e in errors), f"ID {bad_id!r} must be rejected"

    def test_valid_id_characters(self):
        for valid_id in ["test_example", "test-example", "test.example", "test/example", "Test123"]:
            entry = QuarantineEntry(
                id=valid_id,
                owner_team="auth-team",
                issue="https://github.com/example/issues/123",
                reason="Reason",
                created=date(2026, 10, 1),
                expires=date(2026, 11, 1),
            )
            errors = entry.validate_id_format()
            assert errors == [], f"ID '{valid_id}' should be valid"

    def test_owner_team_empty(self):
        entry = QuarantineEntry(
            id="test_example",
            owner_team="",
            issue="https://github.com/example/issues/123",
            reason="Reason",
            created=date(2026, 10, 1),
            expires=date(2026, 11, 1),
        )
        errors = entry.validate_owner_team()
        assert "owner_team: empty" in errors

    def test_owner_team_looks_like_email(self):
        entry = QuarantineEntry(
            id="test_example",
            owner_team="john@example.com",
            issue="https://github.com/example/issues/123",
            reason="Reason",
            created=date(2026, 10, 1),
            expires=date(2026, 11, 1),
        )
        errors = entry.validate_owner_team()
        assert any("looks like an email" in e for e in errors)

    def test_issue_empty(self):
        entry = QuarantineEntry(
            id="test_example",
            owner_team="auth-team",
            issue="",
            reason="Reason",
            created=date(2026, 10, 1),
            expires=date(2026, 11, 1),
        )
        errors = entry.validate_issue()
        assert "issue: empty" in errors

    def test_issue_not_url(self):
        entry = QuarantineEntry(
            id="test_example",
            owner_team="auth-team",
            issue="not-a-url",
            reason="Reason",
            created=date(2026, 10, 1),
            expires=date(2026, 11, 1),
        )
        errors = entry.validate_issue()
        assert any("must be a URL" in e for e in errors)

    def test_issue_valid_urls(self):
        for url in [
            "http://example.com",
            "https://github.com/issues/123",
            "https://gitlab.com/-/issues/1",
        ]:
            entry = QuarantineEntry(
                id="test_example",
                owner_team="auth-team",
                issue=url,
                reason="Reason",
                created=date(2026, 10, 1),
                expires=date(2026, 11, 1),
            )
            errors = entry.validate_issue()
            assert errors == [], f"URL '{url}' should be valid"

    def test_reason_empty(self):
        entry = QuarantineEntry(
            id="test_example",
            owner_team="auth-team",
            issue="https://github.com/example/issues/123",
            reason="",
            created=date(2026, 10, 1),
            expires=date(2026, 11, 1),
        )
        errors = entry.validate_reason()
        assert "reason: empty or whitespace only" in errors

    def test_reason_whitespace_only(self):
        entry = QuarantineEntry(
            id="test_example",
            owner_team="auth-team",
            issue="https://github.com/example/issues/123",
            reason="   ",
            created=date(2026, 10, 1),
            expires=date(2026, 11, 1),
        )
        errors = entry.validate_reason()
        assert "reason: empty or whitespace only" in errors

    def test_expired_today(self):
        entry = QuarantineEntry(
            id="test_example",
            owner_team="auth-team",
            issue="https://github.com/example/issues/123",
            reason="Reason",
            created=date(2026, 10, 1),
            expires=date(2026, 10, 15),  # today
        )
        errors = entry.validate_dates(date(2026, 10, 15))
        assert any("expires" in e and "<= today" in e for e in errors)

    def test_expired_past(self):
        entry = QuarantineEntry(
            id="test_example",
            owner_team="auth-team",
            issue="https://github.com/example/issues/123",
            reason="Reason",
            created=date(2026, 10, 1),
            expires=date(2026, 10, 10),
        )
        errors = entry.validate_dates(date(2026, 10, 15))
        assert any("expires" in e and "<= today" in e for e in errors)

    def test_not_expired_future(self):
        entry = QuarantineEntry(
            id="test_example",
            owner_team="auth-team",
            issue="https://github.com/example/issues/123",
            reason="Reason",
            created=date(2026, 10, 1),
            expires=date(2026, 11, 1),
        )
        errors = entry.validate_dates(date(2026, 10, 15))
        assert not any("expires" in e for e in errors)

    def test_created_after_expires(self):
        entry = QuarantineEntry(
            id="test_example",
            owner_team="auth-team",
            issue="https://github.com/example/issues/123",
            reason="Reason",
            created=date(2026, 11, 1),
            expires=date(2026, 10, 1),
        )
        errors = entry.validate_dates(date(2026, 10, 15))
        assert any("created" in e and ">" in e and "expires" in e for e in errors)

    def test_max_age_exceeded(self):
        entry = QuarantineEntry(
            id="test_example",
            owner_team="auth-team",
            issue="https://github.com/example/issues/123",
            reason="Reason",
            created=date(2026, 9, 1),
            expires=date(2026, 11, 1),
        )
        errors = entry.validate_dates(date(2026, 10, 15), max_age_days=30)
        assert any("max_age" in e and "30" in e for e in errors)

    def test_max_age_not_exceeded(self):
        entry = QuarantineEntry(
            id="test_example",
            owner_team="auth-team",
            issue="https://github.com/example/issues/123",
            reason="Reason",
            created=date(2026, 10, 1),
            expires=date(2026, 11, 1),
        )
        errors = entry.validate_dates(date(2026, 10, 15), max_age_days=30)
        assert not any("max_age" in e for e in errors)


class TestPolicy:
    def test_valid_policy(self):
        policy = Policy(max_age_days=30, max_entries_per_team=5, max_total_entries=20)
        assert policy.validate() == []

    def test_invalid_max_age_days(self):
        policy = Policy(max_age_days=0)
        assert "max_age_days: must be positive" in policy.validate()

    def test_invalid_max_entries_per_team(self):
        policy = Policy(max_entries_per_team=-1)
        assert "max_entries_per_team: must be positive" in policy.validate()

    def test_invalid_max_total_entries(self):
        policy = Policy(max_total_entries=0)
        assert "max_total_entries: must be positive" in policy.validate()

    def test_none_values_ok(self):
        policy = Policy(max_age_days=None, max_entries_per_team=None, max_total_entries=None)
        assert policy.validate() == []


class TestLedger:
    def test_get_entries_by_team(self):
        entries = (
            QuarantineEntry("t1", "team-a", "https://x", "r", date(2026, 1, 1), date(2026, 2, 1)),
            QuarantineEntry("t2", "team-b", "https://x", "r", date(2026, 1, 1), date(2026, 2, 1)),
            QuarantineEntry("t3", "team-a", "https://x", "r", date(2026, 1, 1), date(2026, 2, 1)),
        )
        ledger = Ledger(entries=entries, policy=Policy())
        team_a = ledger.get_entries_by_team("team-a")
        assert len(team_a) == 2
        assert all(e.owner_team == "team-a" for e in team_a)

    def test_get_duplicate_ids(self):
        entries = (
            QuarantineEntry(
                "same-id", "team-a", "https://x", "r", date(2026, 1, 1), date(2026, 2, 1)
            ),
            QuarantineEntry(
                "same-id", "team-b", "https://x", "r", date(2026, 1, 1), date(2026, 2, 1)
            ),
            QuarantineEntry(
                "other-id", "team-a", "https://x", "r", date(2026, 1, 1), date(2026, 2, 1)
            ),
        )
        ledger = Ledger(entries=entries, policy=Policy())
        dupes = ledger.get_duplicate_ids()
        assert "same-id" in dupes
        assert len(dupes["same-id"]) == 2
        assert "other-id" not in dupes

    def test_no_duplicates(self):
        entries = (
            QuarantineEntry("id1", "team-a", "https://x", "r", date(2026, 1, 1), date(2026, 2, 1)),
            QuarantineEntry("id2", "team-b", "https://x", "r", date(2026, 1, 1), date(2026, 2, 1)),
        )
        ledger = Ledger(entries=entries, policy=Policy())
        assert ledger.get_duplicate_ids() == {}
