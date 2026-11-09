"""Inventory checking for quarantine ledger."""


class InventoryChecker:
    """Checks test IDs against a known inventory."""

    def __init__(self, inventory: set[str]):
        self.inventory = inventory

    def has_entry(self, test_id: str) -> bool:
        """Check if a test ID exists in inventory (exact match only)."""
        return test_id in self.inventory

    def missing_entries(self, test_ids: set[str]) -> set[str]:
        """Return test IDs not found in inventory."""
        return test_ids - self.inventory

    @property
    def count(self) -> int:
        return len(self.inventory)
