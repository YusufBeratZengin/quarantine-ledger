"""The shipped example files must behave as the README says they do."""

from datetime import date
from pathlib import Path

from quarantine_ledger.policy import check_ledger
from quarantine_ledger.reader import load_inventory, parse_quarantine_toml

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


def test_example_ledger_matches_documented_output():
    ledger = parse_quarantine_toml(EXAMPLES / "quarantine.toml")
    inventory = load_inventory(EXAMPLES / "tests.json")

    result = check_ledger(ledger, date(2026, 11, 2), inventory)

    by_entry = [(finding.code, finding.entry_id) for finding in result.findings]
    assert result.exit_code == 1
    assert ("EXPIRED", "test_login_timeout") in by_entry
    assert ("EXPIRED", "test_expired_example") in by_entry
    assert ("MISSING_FROM_INVENTORY", "test_expired_example") in by_entry
    # The two tests listed in the inventory and still inside their window are quiet.
    assert not any(finding.entry_id == "test_payment_retry" for finding in result.findings)
