"""Tests for inventory module."""

from quarantine_ledger.inventory import InventoryChecker


class TestInventoryChecker:
    def test_has_entry_exact_match(self):
        checker = InventoryChecker({"test_login", "test_logout", "test_payment"})
        assert checker.has_entry("test_login") is True
        assert checker.has_entry("test_payment") is True

    def test_has_entry_no_match(self):
        checker = InventoryChecker({"test_login", "test_logout"})
        assert checker.has_entry("test_payment") is False
        assert checker.has_entry("test_login_timeout") is False  # no wildcards

    def test_missing_entries(self):
        checker = InventoryChecker({"test_login", "test_logout"})
        missing = checker.missing_entries({"test_login", "test_payment", "test_signup"})
        assert missing == {"test_payment", "test_signup"}

    def test_missing_entries_none(self):
        checker = InventoryChecker({"test_login", "test_logout"})
        missing = checker.missing_entries({"test_login", "test_logout"})
        assert missing == set()

    def test_count(self):
        checker = InventoryChecker({"test1", "test2", "test3"})
        assert checker.count == 3

    def test_empty_inventory(self):
        checker = InventoryChecker(set())
        assert checker.has_entry("anything") is False
        assert checker.count == 0
        assert checker.missing_entries({"test1"}) == {"test1"}
