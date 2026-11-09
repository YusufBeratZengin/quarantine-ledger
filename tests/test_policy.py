"""Tests for policy module."""

from datetime import date

from quarantine_ledger.policy import check_ledger
from quarantine_ledger.schema import Ledger, Policy, QuarantineEntry


def make_entry(
    id: str,
    owner_team: str = "team-a",
    issue: str = "https://github.com/example/issues/1",
    reason: str = "Valid reason",
    created: date = date(2026, 10, 1),
    expires: date = date(2026, 11, 1),
) -> QuarantineEntry:
    return QuarantineEntry(id, owner_team, issue, reason, created, expires)


class TestCheckLedger:
    def test_valid_ledger_no_findings(self):
        ledger = Ledger(
            entries=(make_entry("test1"), make_entry("test2")),
            policy=Policy(),
        )
        result = check_ledger(ledger, date(2026, 10, 15))
        assert not result.has_errors
        assert result.exit_code == 0
        assert result.checked_entries == 2

    def test_expired_entry(self):
        ledger = Ledger(
            entries=(make_entry("test1", expires=date(2026, 10, 10)),),
            policy=Policy(),
        )
        result = check_ledger(ledger, date(2026, 10, 15))
        assert result.has_errors
        assert result.exit_code == 1
        assert any(f.code == "EXPIRED" for f in result.findings)

    def test_expires_today(self):
        ledger = Ledger(
            entries=(make_entry("test1", expires=date(2026, 10, 15)),),
            policy=Policy(),
        )
        result = check_ledger(ledger, date(2026, 10, 15))
        assert result.has_errors
        assert any(f.code == "EXPIRED" for f in result.findings)

    def test_created_after_expires(self):
        ledger = Ledger(
            entries=(make_entry("test1", created=date(2026, 11, 1), expires=date(2026, 10, 1)),),
            policy=Policy(),
        )
        result = check_ledger(ledger, date(2026, 10, 15))
        assert result.has_errors
        assert any(f.code == "INVALID_DATE" for f in result.findings)

    def test_max_age_exceeded(self):
        ledger = Ledger(
            entries=(make_entry("test1", created=date(2026, 9, 1), expires=date(2026, 11, 1)),),
            policy=Policy(max_age_days=30),
        )
        result = check_ledger(ledger, date(2026, 10, 15))
        assert result.has_errors
        assert any(f.code == "MAX_AGE_EXCEEDED" for f in result.findings)

    def test_empty_id(self):
        entry = make_entry("")
        ledger = Ledger(entries=(entry,), policy=Policy())
        result = check_ledger(ledger, date(2026, 10, 15))
        assert any(f.code == "EMPTY_ID" for f in result.findings)

    def test_empty_owner_team(self):
        entry = make_entry("test1", owner_team="")
        ledger = Ledger(entries=(entry,), policy=Policy())
        result = check_ledger(ledger, date(2026, 10, 15))
        assert any(f.code == "EMPTY_OWNER_TEAM" for f in result.findings)

    def test_owner_team_looks_like_email(self):
        entry = make_entry("test1", owner_team="john@example.com")
        ledger = Ledger(entries=(entry,), policy=Policy())
        result = check_ledger(ledger, date(2026, 10, 15))
        assert any(f.code == "OWNER_TEAM_LOOKS_LIKE_EMAIL" for f in result.findings)

    def test_empty_issue(self):
        entry = make_entry("test1", issue="")
        ledger = Ledger(entries=(entry,), policy=Policy())
        result = check_ledger(ledger, date(2026, 10, 15))
        assert any(f.code == "EMPTY_ISSUE" for f in result.findings)

    def test_invalid_issue_url(self):
        entry = make_entry("test1", issue="not-a-url")
        ledger = Ledger(entries=(entry,), policy=Policy())
        result = check_ledger(ledger, date(2026, 10, 15))
        assert any(f.code == "INVALID_ISSUE_URL" for f in result.findings)

    def test_empty_reason(self):
        entry = make_entry("test1", reason="")
        ledger = Ledger(entries=(entry,), policy=Policy())
        result = check_ledger(ledger, date(2026, 10, 15))
        assert any(f.code == "EMPTY_REASON" for f in result.findings)

    def test_whitespace_reason(self):
        entry = make_entry("test1", reason="   ")
        ledger = Ledger(entries=(entry,), policy=Policy())
        result = check_ledger(ledger, date(2026, 10, 15))
        assert any(f.code == "EMPTY_REASON" for f in result.findings)

    def test_duplicate_ids(self):
        entries = (
            make_entry("same-id", owner_team="team-a"),
            make_entry("same-id", owner_team="team-b"),
        )
        ledger = Ledger(entries=entries, policy=Policy())
        result = check_ledger(ledger, date(2026, 10, 15))
        assert result.has_errors
        dupe_findings = [f for f in result.findings if f.code == "DUPLICATE_ID"]
        assert len(dupe_findings) == 2  # one per entry

    def test_duplicate_id_findings_match_entry_count(self):
        # N entries sharing one id yield exactly N DUPLICATE_ID findings.
        for n in (2, 3, 5):
            entries = tuple(make_entry("same-id", owner_team=f"team-{i}") for i in range(n))
            ledger = Ledger(entries=entries, policy=Policy())
            result = check_ledger(ledger, date(2026, 10, 15))
            dupe_findings = [f for f in result.findings if f.code == "DUPLICATE_ID"]
            assert len(dupe_findings) == n

    def test_invalid_id_format_flagged(self):
        for bad_id in ("test example", "test işlem"):
            entry = make_entry(bad_id)
            ledger = Ledger(entries=(entry,), policy=Policy())
            result = check_ledger(ledger, date(2026, 10, 15))
            assert any(f.code == "INVALID_ID" for f in result.findings)
            assert result.exit_code == 2

    def test_inventory_missing(self):
        ledger = Ledger(entries=(make_entry("test1"),), policy=Policy())
        result = check_ledger(ledger, date(2026, 10, 15), inventory={"test2", "test3"})
        assert result.has_errors
        assert any(f.code == "MISSING_FROM_INVENTORY" for f in result.findings)
        assert result.inventory_provided is True

    def test_inventory_present(self):
        ledger = Ledger(entries=(make_entry("test1"),), policy=Policy())
        result = check_ledger(ledger, date(2026, 10, 15), inventory={"test1", "test2"})
        assert not any(f.code == "MISSING_FROM_INVENTORY" for f in result.findings)

    def test_no_inventory_provided(self):
        ledger = Ledger(entries=(make_entry("test1"),), policy=Policy())
        result = check_ledger(ledger, date(2026, 10, 15), inventory=None)
        assert not any(f.code == "MISSING_FROM_INVENTORY" for f in result.findings)
        assert result.inventory_provided is False

    def test_budget_exceeded_total(self):
        ledger = Ledger(
            entries=(make_entry("t1"), make_entry("t2"), make_entry("t3")),
            policy=Policy(max_total_entries=2),
        )
        result = check_ledger(ledger, date(2026, 10, 15))
        assert result.has_errors
        assert any(f.code == "BUDGET_EXCEEDED_TOTAL" for f in result.findings)

    def test_budget_exceeded_per_team(self):
        ledger = Ledger(
            entries=(
                make_entry("t1", owner_team="team-a"),
                make_entry("t2", owner_team="team-a"),
                make_entry("t3", owner_team="team-a"),
            ),
            policy=Policy(max_entries_per_team=2),
        )
        result = check_ledger(ledger, date(2026, 10, 15))
        assert result.has_errors
        assert any(f.code == "BUDGET_EXCEEDED_TEAM" for f in result.findings)

    def test_budget_ok(self):
        ledger = Ledger(
            entries=(make_entry("t1"), make_entry("t2")),
            policy=Policy(max_total_entries=5, max_entries_per_team=3),
        )
        result = check_ledger(ledger, date(2026, 10, 15))
        assert not any(f.code.startswith("BUDGET") for f in result.findings)

    def test_deduplication(self):
        # Same error on same entry should be deduplicated
        make_entry("test1", reason="")  # EMPTY_REASON
        # Also expired
        entry_expired = make_entry("test1", reason="", expires=date(2026, 10, 10))
        ledger = Ledger(entries=(entry_expired,), policy=Policy())
        result = check_ledger(ledger, date(2026, 10, 15))
        # Should have both EXPIRED and EMPTY_REASON but not duplicates
        codes = [f.code for f in result.findings]
        assert codes.count("EXPIRED") == 1
        assert codes.count("EMPTY_REASON") == 1

    def test_exit_code_1_for_expired(self):
        ledger = Ledger(entries=(make_entry("test1", expires=date(2026, 10, 10)),), policy=Policy())
        result = check_ledger(ledger, date(2026, 10, 15))
        assert result.exit_code == 1

    def test_exit_code_1_for_missing_inventory(self):
        ledger = Ledger(entries=(make_entry("test1"),), policy=Policy())
        result = check_ledger(ledger, date(2026, 10, 15), inventory={"other"})
        assert result.exit_code == 1

    def test_exit_code_2_for_budget(self):
        ledger = Ledger(
            entries=(make_entry("t1"), make_entry("t2")), policy=Policy(max_total_entries=1)
        )
        result = check_ledger(ledger, date(2026, 10, 15))
        assert result.exit_code == 2

    def test_exit_code_2_for_duplicate(self):
        entries = (make_entry("same"), make_entry("same"))
        ledger = Ledger(entries=entries, policy=Policy())
        result = check_ledger(ledger, date(2026, 10, 15))
        assert result.exit_code == 2

    def test_exit_code_2_for_empty_fields(self):
        ledger = Ledger(entries=(make_entry("test1", reason=""),), policy=Policy())
        result = check_ledger(ledger, date(2026, 10, 15))
        assert result.exit_code == 2
