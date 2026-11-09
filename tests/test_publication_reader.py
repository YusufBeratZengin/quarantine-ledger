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

    def test_invalid_utf8_toml(self, tmp_path):
        path = tmp_path / "invalid_utf8.toml"
        path.write_bytes(b"\xff\xfe[[entries]]\n")
        with pytest.raises(TomlParseError, match="Failed to decode TOML file as UTF-8"):
            parse_quarantine_toml(path)

    def test_missing_entries(self):
        content = """
[policy]
max_age_days = 30
"""
        path = create_temp_toml(content)
        ledger = parse_quarantine_toml(path)
        # A policy-only file is a valid empty quarantine list, not an error.
        assert ledger.entries == ()
        assert ledger.policy.max_age_days == 30
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


class TestRootKeys:
    """Unknown root keys must fail loudly instead of being ignored.

    A ``[[entry]]`` typo used to be dropped by the reader, so the file looked
    like an empty ledger and ``check`` exited 0 on it.
    """

    def test_entry_table_typo_is_rejected(self):
        content = """
[[entry]]
id = "test1"
owner_team = "team-a"
issue = "https://github.com/example/issues/1"
reason = "Reason"
created = "2026-10-01"
expires = "2026-11-01"
"""
        path = create_temp_toml(content)
        try:
            with pytest.raises(ValidationError) as excinfo:
                parse_quarantine_toml(path)
        finally:
            path.unlink()
        assert any("root: unknown key 'entry'" in m for m in excinfo.value.errors)

    def test_unknown_root_key_is_rejected(self):
        content = """
[policy]
max_age_days = 30

[policies]
max_age_days = 30
"""
        path = create_temp_toml(content)
        try:
            with pytest.raises(ValidationError) as excinfo:
                parse_quarantine_toml(path)
        finally:
            path.unlink()
        assert any("root: unknown key 'policies'" in m for m in excinfo.value.errors)

    def test_empty_file_is_rejected(self):
        """An accidentally emptied file must not pass as a clean gate."""
        path = create_temp_toml("")
        try:
            with pytest.raises(ValidationError) as excinfo:
                parse_quarantine_toml(path)
        finally:
            path.unlink()
        assert excinfo.value.errors == [
            "root: file is empty; expected at least a [policy] table or [[entries]] entries"
        ]


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

    def test_empty_item(self):
        content = '["test1", "   "]'
        path = create_temp_json(content)
        with pytest.raises(ValidationError, match="inventory\\[1\\]: empty test id"):
            load_inventory(path)
        path.unlink()

    @pytest.mark.parametrize("bad_bytes", [b"\xff\xfe[]", b'["test_\x80"]'])
    def test_invalid_utf8_inventory(self, tmp_path, bad_bytes):
        path = tmp_path / "invalid_utf8_inventory.json"
        path.write_bytes(bad_bytes)
        with pytest.raises(TomlParseError, match="Failed to decode inventory file as UTF-8"):
            load_inventory(path)

    def test_missing_inventory_file(self, tmp_path):
        with pytest.raises(TomlParseError, match="Failed to read inventory file"):
            load_inventory(tmp_path / "missing_inventory.json")


class TestPolicyTypeValidation:
    """The [policy] table used to be read with .get() and no type checks.

    A scalar or a wrong-typed value therefore produced an AttributeError /
    TypeError traceback instead of a controlled validation error.
    """

    def _errors(self, content: str) -> list[str]:
        path = create_temp_toml(content)
        try:
            with pytest.raises(ValidationError) as excinfo:
                parse_quarantine_toml(path)
        finally:
            path.unlink()
        return excinfo.value.errors

    def test_policy_not_a_table(self):
        errors = self._errors('policy = "wrong"\n')
        assert errors == ["policy: must be a table, got str"]

    def test_policy_unknown_key(self):
        errors = self._errors("[policy]\nmax_age_day = 30\n")
        assert any("policy: unknown key 'max_age_day'" in message for message in errors)

    def test_policy_wrong_value_type(self):
        errors = self._errors('[policy]\nmax_total_entries = "20"\n')
        assert any(
            "policy.max_total_entries: must be an integer, got str" in message for message in errors
        )

    def test_policy_boolean_rejected(self):
        errors = self._errors("[policy]\nmax_age_days = true\n")
        assert any(
            "policy.max_age_days: must be an integer, got bool" in message for message in errors
        )


class TestEntryTypeValidation:
    def test_entry_field_wrong_type(self):
        content = """
[[entries]]
id = 5
owner_team = "team-a"
issue = "https://github.com/example/issues/1"
reason = "Reason"
created = "2026-10-01"
expires = "2026-11-01"
"""
        path = create_temp_toml(content)
        try:
            with pytest.raises(ValidationError) as excinfo:
                parse_quarantine_toml(path)
        finally:
            path.unlink()
        assert any("entries[0].id: must be a string, got int" in m for m in excinfo.value.errors)

    def test_entry_unknown_key(self):
        content = """
[[entries]]
id = "test1"
owner_team = "team-a"
issue = "https://github.com/example/issues/1"
reason = "Reason"
created = "2026-10-01"
expires = "2026-11-01"
expires_at = "2026-11-01"
"""
        path = create_temp_toml(content)
        try:
            with pytest.raises(ValidationError) as excinfo:
                parse_quarantine_toml(path)
        finally:
            path.unlink()
        assert any("entries[0]: unknown key 'expires_at'" in m for m in excinfo.value.errors)

    def test_missing_date_reported_once(self):
        content = """
[[entries]]
id = "test1"
owner_team = "team-a"
issue = "https://github.com/example/issues/1"
reason = "Reason"
created = "2026-10-01"
"""
        path = create_temp_toml(content)
        try:
            with pytest.raises(ValidationError) as excinfo:
                parse_quarantine_toml(path)
        finally:
            path.unlink()
        assert excinfo.value.errors == ["entries[0].expires: missing, expected YYYY-MM-DD"]
