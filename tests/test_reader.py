"""Tests for reader module."""

import tempfile
from pathlib import Path

import pytest

from quarantine_ledger.reader import (
    TomlParseError,
    ValidationError,
    load_inventory,
    parse_quarantine_toml,
)
from quarantine_ledger.schema import Ledger


def create_temp_toml(content: str) -> Path:
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write(content)
        return Path(f.name)


def create_temp_json(content: str) -> Path:
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write(content)
        return Path(f.name)


class TestParseQuarantineToml:
    def test_valid_minimal(self):
        content = """
[[entries]]
id = "test1"
owner_team = "team-a"
issue = "https://github.com/example/issues/1"
reason = "Reason"
created = "2026-10-01"
expires = "2026-11-01"
"""
        path = create_temp_toml(content)
        ledger = parse_quarantine_toml(path)
        assert isinstance(ledger, Ledger)
        assert len(ledger.entries) == 1
        assert ledger.entries[0].id == "test1"
        path.unlink()

    def test_valid_with_policy(self):
        content = """
[policy]
max_age_days = 30
max_entries_per_team = 5
max_total_entries = 20

[[entries]]
id = "test1"
owner_team = "team-a"
issue = "https://github.com/example/issues/1"
reason = "Reason"
created = "2026-10-01"
expires = "2026-11-01"
"""
        path = create_temp_toml(content)
        ledger = parse_quarantine_toml(path)
        assert ledger.policy.max_age_days == 30
        assert ledger.policy.max_entries_per_team == 5
        assert ledger.policy.max_total_entries == 20
        path.unlink()

    def test_multiple_entries(self):
        content = """
[[entries]]
id = "test1"
owner_team = "team-a"
issue = "https://github.com/example/issues/1"
reason = "Reason 1"
created = "2026-10-01"
expires = "2026-11-01"

[[entries]]
id = "test2"
owner_team = "team-b"
issue = "https://github.com/example/issues/2"
reason = "Reason 2"
created = "2026-10-02"
expires = "2026-11-02"
"""
        path = create_temp_toml(content)
        ledger = parse_quarantine_toml(path)
        assert len(ledger.entries) == 2
        path.unlink()

    def test_invalid_toml_syntax(self):
        content = """
[[entries]]
id = "test1"
owner_team = "team-a"
issue = "https://github.com/example/issues/1"
reason = "Reason"
created = "2026-10-01"
expires = "2026-11-01"
invalid = 
"""
        path = create_temp_toml(content)
        with pytest.raises(TomlParseError, match="Failed to parse TOML"):
            parse_quarantine_toml(path)
        path.unlink()

    def test_missing_entries(self):
        content = """
[policy]
max_age_days = 30
"""
        path = create_temp_toml(content)
        ledger = parse_quarantine_toml(path)
        assert ledger.entries == ()
        path.unlink()

    def test_entries_not_list(self):
        content = """
entries = "not-a-list"
"""
        path = create_temp_toml(content)
        with pytest.raises(ValidationError, match="entries: must be a list"):
            parse_quarantine_toml(path)
        path.unlink()

    def test_entry_not_table(self):
        content = """
entries = ["not-a-table"]
"""
        path = create_temp_toml(content)
        with pytest.raises(ValidationError, match="entries\\[0\\]: must be a table"):
            parse_quarantine_toml(path)
        path.unlink()

    def test_invalid_date_format(self):
        content = """
[[entries]]
id = "test1"
owner_team = "team-a"
issue = "https://github.com/example/issues/1"
reason = "Reason"
created = "01-10-2026"
expires = "2026-11-01"
"""
        path = create_temp_toml(content)
        with pytest.raises(ValidationError, match="Invalid date format"):
            parse_quarantine_toml(path)
        path.unlink()

    def test_policy_validation_error(self):
        content = """
[policy]
max_age_days = 0

[[entries]]
id = "test1"
owner_team = "team-a"
issue = "https://github.com/example/issues/1"
reason = "Reason"
created = "2026-10-01"
expires = "2026-11-01"
"""
        path = create_temp_toml(content)
        with pytest.raises(ValidationError, match="policy: max_age_days: must be positive"):
            parse_quarantine_toml(path)
        path.unlink()


class TestParseQuarantineTomlTypeValidation:
    """Field types must be validated at the schema boundary."""

    def test_numeric_id_rejected(self):
        content = """
[[entries]]
id = 123
owner_team = "team-a"
issue = "https://github.com/example/issues/1"
reason = "Reason"
created = "2026-10-01"
expires = "2026-11-01"
"""
        path = create_temp_toml(content)
        with pytest.raises(ValidationError, match="id: must be a string, got integer"):
            parse_quarantine_toml(path)
        path.unlink()

    def test_boolean_text_field_rejected(self):
        content = """
[[entries]]
id = "test1"
owner_team = "team-a"
issue = "https://github.com/example/issues/1"
reason = true
created = "2026-10-01"
expires = "2026-11-01"
"""
        path = create_temp_toml(content)
        with pytest.raises(ValidationError, match="reason: must be a string, got boolean"):
            parse_quarantine_toml(path)
        path.unlink()

    def test_numeric_owner_team_rejected(self):
        content = """
[[entries]]
id = "test1"
owner_team = 123
issue = "https://github.com/example/issues/1"
reason = "Reason"
created = "2026-10-01"
expires = "2026-11-01"
"""
        path = create_temp_toml(content)
        with pytest.raises(ValidationError, match="owner_team: must be a string"):
            parse_quarantine_toml(path)
        path.unlink()

    def test_local_toml_date_rejected(self):
        content = """
[[entries]]
id = "test1"
owner_team = "team-a"
issue = "https://github.com/example/issues/1"
reason = "Reason"
created = 2026-10-01
expires = 2026-11-01
"""
        path = create_temp_toml(content)
        with pytest.raises(ValidationError, match="TOML local dates are not supported"):
            parse_quarantine_toml(path)
        path.unlink()

    def test_policy_not_a_table_rejected(self):
        content = """
policy = "metin"

[[entries]]
id = "test1"
owner_team = "team-a"
issue = "https://github.com/example/issues/1"
reason = "Reason"
created = "2026-10-01"
expires = "2026-11-01"
"""
        path = create_temp_toml(content)
        with pytest.raises(ValidationError, match="policy: must be a table"):
            parse_quarantine_toml(path)
        path.unlink()

    def test_policy_wrong_field_type_rejected(self):
        content = """
[policy]
max_age_days = "30"

[[entries]]
id = "test1"
owner_team = "team-a"
issue = "https://github.com/example/issues/1"
reason = "Reason"
created = "2026-10-01"
expires = "2026-11-01"
"""
        path = create_temp_toml(content)
        with pytest.raises(
            ValidationError,
            match="policy.max_age_days: must be an integer, got str",
        ):
            parse_quarantine_toml(path)
        path.unlink()

    def test_policy_boolean_field_rejected(self):
        content = """
[policy]
max_total_entries = true
"""
        path = create_temp_toml(content)
        with pytest.raises(
            ValidationError,
            match="policy.max_total_entries: must be an integer, got boolean",
        ):
            parse_quarantine_toml(path)
        path.unlink()


class TestLoadInventory:
    def test_valid_inventory(self):
        content = '["test1", "test2", "test3"]'
        path = create_temp_json(content)
        inventory = load_inventory(path)
        assert inventory == {"test1", "test2", "test3"}
        path.unlink()

    def test_empty_inventory(self):
        content = "[]"
        path = create_temp_json(content)
        inventory = load_inventory(path)
        assert inventory == set()
        path.unlink()

    def test_invalid_json(self):
        content = "[invalid json"
        path = create_temp_json(content)
        with pytest.raises(TomlParseError, match="Failed to parse inventory JSON"):
            load_inventory(path)
        path.unlink()

    def test_not_a_list(self):
        content = '{"not": "a-list"}'
        path = create_temp_json(content)
        with pytest.raises(ValidationError, match="inventory: must be a list"):
            load_inventory(path)
        path.unlink()

    def test_non_string_items(self):
        content = '["test1", 123, "test3"]'
        path = create_temp_json(content)
        with pytest.raises(ValidationError, match="inventory\\[1\\]: must be a string"):
            load_inventory(path)
        path.unlink()
