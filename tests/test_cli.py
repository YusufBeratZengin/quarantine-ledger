"""Tests for CLI module."""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

from quarantine_ledger.cli import main

SRC_DIR = Path(__file__).resolve().parents[1] / "src"


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    """Run the CLI in a subprocess so real exit codes and stderr are observable."""
    env = dict(os.environ)
    env["PYTHONPATH"] = str(SRC_DIR) + os.pathsep + env.get("PYTHONPATH", "")
    return subprocess.run(
        [sys.executable, "-m", "quarantine_ledger.cli", *args],
        capture_output=True,
        text=True,
        env=env,
    )


def create_temp_file(content: str, suffix: str) -> Path:
    with tempfile.NamedTemporaryFile(mode="w", suffix=suffix, delete=False, encoding="utf-8") as f:
        f.write(content)
        return Path(f.name)


class TestCLICheck:
    def test_check_valid(self):
        toml_content = """
[[entries]]
id = "test1"
owner_team = "team-a"
issue = "https://github.com/example/issues/1"
reason = "Reason"
created = "2026-10-01"
expires = "2026-11-01"
"""
        toml_path = create_temp_file(toml_content, ".toml")
        try:
            exit_code = main(["check", str(toml_path), "--today", "2026-10-15"])
            assert exit_code == 0
        finally:
            toml_path.unlink()

    def test_check_expired(self):
        toml_content = """
[[entries]]
id = "test1"
owner_team = "team-a"
issue = "https://github.com/example/issues/1"
reason = "Reason"
created = "2026-10-01"
expires = "2026-10-10"
"""
        toml_path = create_temp_file(toml_content, ".toml")
        try:
            exit_code = main(["check", str(toml_path), "--today", "2026-10-15"])
            assert exit_code == 1
        finally:
            toml_path.unlink()

    def test_check_invalid_date(self):
        toml_content = """
[[entries]]
id = "test1"
owner_team = "team-a"
issue = "https://github.com/example/issues/1"
reason = "Reason"
created = "2026-11-01"
expires = "2026-10-01"
"""
        toml_path = create_temp_file(toml_content, ".toml")
        try:
            exit_code = main(["check", str(toml_path), "--today", "2026-10-15"])
            assert exit_code == 1
        finally:
            toml_path.unlink()

    def test_check_with_inventory_missing(self):
        toml_content = """
[[entries]]
id = "test1"
owner_team = "team-a"
issue = "https://github.com/example/issues/1"
reason = "Reason"
created = "2026-10-01"
expires = "2026-11-01"
"""
        json_content = '["test2", "test3"]'
        toml_path = create_temp_file(toml_content, ".toml")
        json_path = create_temp_file(json_content, ".json")
        try:
            exit_code = main([
                "check",
                str(toml_path),
                "--inventory",
                str(json_path),
                "--today",
                "2026-10-15",
            ])
            assert exit_code == 1
        finally:
            toml_path.unlink()
            json_path.unlink()

    def test_check_with_inventory_present(self):
        toml_content = """
[[entries]]
id = "test1"
owner_team = "team-a"
issue = "https://github.com/example/issues/1"
reason = "Reason"
created = "2026-10-01"
expires = "2026-11-01"
"""
        json_content = '["test1", "test2"]'
        toml_path = create_temp_file(toml_content, ".toml")
        json_path = create_temp_file(json_content, ".json")
        try:
            exit_code = main([
                "check",
                str(toml_path),
                "--inventory",
                str(json_path),
                "--today",
                "2026-10-15",
            ])
            assert exit_code == 0
        finally:
            toml_path.unlink()
            json_path.unlink()

    def test_check_json_format(self):
        toml_content = """
[[entries]]
id = "test1"
owner_team = "team-a"
issue = "https://github.com/example/issues/1"
reason = "Reason"
created = "2026-10-01"
expires = "2026-10-10"
"""
        toml_path = create_temp_file(toml_content, ".toml")
        try:
            import io
            import sys

            old_stdout = sys.stdout
            sys.stdout = io.StringIO()
            try:
                exit_code = main([
                    "check",
                    str(toml_path),
                    "--today",
                    "2026-10-15",
                    "--format",
                    "json",
                ])
                output = sys.stdout.getvalue()
            finally:
                sys.stdout = old_stdout
            assert exit_code == 1
            data = json.loads(output)
            assert data["exit_code"] == 1
            assert len(data["findings"]) > 0
            assert data["findings"][0]["code"] == "EXPIRED"
        finally:
            toml_path.unlink()

    def test_check_budget_exceeded(self):
        toml_content = """
[policy]
max_total_entries = 1

[[entries]]
id = "test1"
owner_team = "team-a"
issue = "https://github.com/example/issues/1"
reason = "Reason"
created = "2026-10-01"
expires = "2026-11-01"

[[entries]]
id = "test2"
owner_team = "team-a"
issue = "https://github.com/example/issues/2"
reason = "Reason"
created = "2026-10-01"
expires = "2026-11-01"
"""
        toml_path = create_temp_file(toml_content, ".toml")
        try:
            exit_code = main(["check", str(toml_path), "--today", "2026-10-15"])
            assert exit_code == 2
        finally:
            toml_path.unlink()


class TestCLIReport:
    def test_report_json(self):
        toml_content = """
[policy]
max_age_days = 30

[[entries]]
id = "test1"
owner_team = "team-a"
issue = "https://github.com/example/issues/1"
reason = "Reason"
created = "2026-10-01"
expires = "2026-11-01"
"""
        toml_path = create_temp_file(toml_content, ".toml")
        try:
            import io
            import sys

            old_stdout = sys.stdout
            sys.stdout = io.StringIO()
            try:
                exit_code = main([
                    "report",
                    str(toml_path),
                    "--today",
                    "2026-10-15",
                    "--format",
                    "json",
                ])
                output = sys.stdout.getvalue()
            finally:
                sys.stdout = old_stdout
            assert exit_code == 0
            data = json.loads(output)
            assert "policy" in data
            assert "summary" in data
            assert "entries" in data
            assert "findings" in data
            assert data["summary"]["total_entries"] == 1
        finally:
            toml_path.unlink()

    def test_report_summary(self):
        toml_content = """
[[entries]]
id = "test1"
owner_team = "team-a"
issue = "https://github.com/example/issues/1"
reason = "Reason"
created = "2026-10-01"
expires = "2026-11-01"
"""
        toml_path = create_temp_file(toml_content, ".toml")
        try:
            import io
            import sys

            old_stdout = sys.stdout
            sys.stdout = io.StringIO()
            try:
                exit_code = main([
                    "report",
                    str(toml_path),
                    "--today",
                    "2026-10-15",
                    "--format",
                    "summary",
                ])
                output = sys.stdout.getvalue()
            finally:
                sys.stdout = old_stdout
            assert exit_code == 0
            assert "Quarantine Ledger Report" in output
            assert "Total entries: 1" in output
        finally:
            toml_path.unlink()


class TestCLIDemo:
    def test_demo_creates_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            demo_dir = Path(tmpdir) / "demo"
            exit_code = main(["demo", "--dir", str(demo_dir)])
            assert exit_code == 0
            assert (demo_dir / "quarantine.toml").exists()
            assert (demo_dir / "tests.json").exists()
            assert (demo_dir / "README.md").exists()

            # Verify content
            toml_content = (demo_dir / "quarantine.toml").read_text()
            assert "test_login_timeout" in toml_content
            assert "test_expired_example" in toml_content

            json_content = (demo_dir / "tests.json").read_text()
            assert "test_login_timeout" in json_content
            assert "test_expired_example" not in json_content  # intentionally missing


class TestMainErrors:
    def test_invalid_toml(self):
        toml_content = "invalid toml [[["
        toml_path = create_temp_file(toml_content, ".toml")
        try:
            exit_code = main(["check", str(toml_path)])
            assert exit_code == 2
        finally:
            toml_path.unlink()

    def test_missing_file(self):
        exit_code = main(["check", "/nonexistent/path.toml"])
        assert exit_code == 2

    def test_no_command(self):
        exit_code = main([])
        assert exit_code == 2


VALID_ENTRY_TOML = """
[[entries]]
id = "test1"
owner_team = "team-a"
issue = "https://github.com/example/issues/1"
reason = "Reason"
created = "2026-10-01"
expires = "2026-11-01"
"""


class TestCLIReportJsonDates:
    def test_report_json_serializes_all_dates(self):
        toml_path = create_temp_file(VALID_ENTRY_TOML, ".toml")
        try:
            proc = run_cli("report", str(toml_path), "--today", "2026-10-15", "--format", "json")
        finally:
            toml_path.unlink()

        assert proc.returncode == 0, proc.stderr
        assert "Traceback" not in proc.stderr
        data = json.loads(proc.stdout)
        entry = data["entries"][0]
        assert isinstance(entry["created"], str)
        assert isinstance(entry["expires"], str)
        assert entry["created"] == "2026-10-01"
        assert entry["expires"] == "2026-11-01"


class TestCLITodayValidation:
    @pytest.mark.parametrize("command", ["check", "report"])
    def test_invalid_today_exits_2_without_traceback(self, command):
        toml_path = create_temp_file(VALID_ENTRY_TOML, ".toml")
        try:
            proc = run_cli(command, str(toml_path), "--today", "2026-13-99")
        finally:
            toml_path.unlink()

        assert proc.returncode == 2
        assert "Traceback" not in proc.stderr
        assert "invalid --today" in proc.stderr
        assert "Invalid date format" in proc.stderr

    @pytest.mark.parametrize("command", ["check", "report"])
    def test_empty_today_is_invalid(self, command):
        # Before: an explicit "" was treated like a missing option and today's
        # UTC date was used silently.
        toml_path = create_temp_file(VALID_ENTRY_TOML, ".toml")
        try:
            proc = run_cli(command, str(toml_path), "--today", "")
        finally:
            toml_path.unlink()

        assert proc.returncode == 2
        assert "Traceback" not in proc.stderr
        assert "invalid --today" in proc.stderr
        assert "Invalid date format ''" in proc.stderr
        assert proc.stdout == ""

    def test_omitted_today_defaults_to_utc_today(self):
        toml_content = """
[[entries]]
id = "test1"
owner_team = "team-a"
issue = "https://github.com/example/issues/1"
reason = "Reason"
created = "2020-01-01"
expires = "2099-01-01"
"""
        toml_path = create_temp_file(toml_content, ".toml")
        try:
            proc = run_cli("check", str(toml_path))
        finally:
            toml_path.unlink()

        assert proc.returncode == 0, proc.stderr
        assert "OK:" in proc.stdout


class TestCLITypeValidation:
    def test_numeric_id_is_rejected(self):
        # `id = 123` used to be accepted silently (exit 0 / OK).
        toml_content = VALID_ENTRY_TOML.replace('id = "test1"', "id = 123")
        toml_path = create_temp_file(toml_content, ".toml")
        try:
            proc = run_cli("check", str(toml_path), "--today", "2026-10-15")
        finally:
            toml_path.unlink()

        assert proc.returncode == 2
        assert "Traceback" not in proc.stderr
        assert "id: must be a string" in proc.stderr
        assert "OK:" not in proc.stdout

    def test_policy_not_a_table_is_rejected(self):
        # `policy = "metin"` used to raise AttributeError.
        toml_content = 'policy = "metin"\n' + VALID_ENTRY_TOML
        toml_path = create_temp_file(toml_content, ".toml")
        try:
            proc = run_cli("report", str(toml_path), "--today", "2026-10-15")
        finally:
            toml_path.unlink()

        assert proc.returncode == 2
        assert "Traceback" not in proc.stderr
        assert "policy: must be a table" in proc.stderr

    def test_local_toml_date_is_rejected(self):
        # Unquoted TOML dates come back as datetime.date, not str.
        toml_content = VALID_ENTRY_TOML.replace('created = "2026-10-01"', "created = 2026-10-01")
        toml_path = create_temp_file(toml_content, ".toml")
        try:
            proc = run_cli("check", str(toml_path), "--today", "2026-10-15")
        finally:
            toml_path.unlink()

        assert proc.returncode == 2
        assert "Traceback" not in proc.stderr
        assert "TOML local dates are not supported" in proc.stderr


class TestCLIInvalidIdFormat:
    @pytest.mark.parametrize("bad_id", ["test example", "test işlem"])
    def test_check_flags_invalid_id_characters(self, bad_id):
        # Same rule as schema.validate_id_format: spaces and non-ASCII letters
        # are not allowed in test IDs.
        toml_content = VALID_ENTRY_TOML.replace('id = "test1"', f'id = "{bad_id}"')
        toml_path = create_temp_file(toml_content, ".toml")
        try:
            proc = run_cli("check", str(toml_path), "--today", "2026-10-15", "--format", "json")
        finally:
            toml_path.unlink()

        assert proc.returncode == 2
        assert "Traceback" not in proc.stderr
        data = json.loads(proc.stdout)
        assert any(f["code"] == "INVALID_ID" for f in data["findings"])

    @pytest.mark.parametrize("toml_escaped_id", ["test1\\n", "test1\\r\\n"])
    def test_check_flags_trailing_line_ending(self, toml_escaped_id):
        # TOML decodes "\n" / "\r\n" into a real trailing line ending in the id.
        # `$` used to match before it, so check exited 0 with "OK".
        toml_content = VALID_ENTRY_TOML.replace('id = "test1"', f'id = "{toml_escaped_id}"')
        toml_path = create_temp_file(toml_content, ".toml")
        try:
            proc = run_cli("check", str(toml_path), "--today", "2026-10-15", "--format", "json")
        finally:
            toml_path.unlink()

        assert proc.returncode == 2
        assert "Traceback" not in proc.stderr
        data = json.loads(proc.stdout)
        assert any(f["code"] == "INVALID_ID" for f in data["findings"])
        assert "OK:" not in proc.stdout


class TestPublicationRegressions:
    def test_demo_preserves_existing_ledger(self, tmp_path):
        ledger = tmp_path / "quarantine.toml"
        ledger.write_bytes(b"# synthetic sentinel\n")
        proc = run_cli("demo", "--dir", str(tmp_path))
        assert proc.returncode == 2
        assert ledger.read_bytes() == b"# synthetic sentinel\n"
        assert not (tmp_path / "tests.json").exists()

    def test_misspelled_root_is_rejected(self, tmp_path):
        ledger = tmp_path / "quarantine.toml"
        ledger.write_text(VALID_ENTRY_TOML.replace("[[entries]]", "[[entry]]"), encoding="utf-8")
        proc = run_cli("check", str(ledger), "--today", "2026-10-15")
        assert proc.returncode == 2
        assert "unknown key 'entry'" in proc.stderr

    @pytest.mark.parametrize(
        "field,value,code",
        [
            ("owner_team", "   ", "EMPTY_OWNER_TEAM"),
            ("issue", "https://", "INVALID_ISSUE_URL"),
        ],
    )
    def test_field_validation_matches_schema(self, tmp_path, field, value, code):
        from dataclasses import replace

        from quarantine_ledger.reader import parse_quarantine_toml

        ledger = tmp_path / "quarantine.toml"
        ledger.write_text(VALID_ENTRY_TOML, encoding="utf-8")
        entry = replace(parse_quarantine_toml(ledger).entries[0], **{field: value})
        validator = getattr(entry, f"validate_{field}")
        assert validator()
        old = "team-a" if field == "owner_team" else "https://github.com/example/issues/1"
        ledger.write_text(VALID_ENTRY_TOML.replace(old, value), encoding="utf-8")
        proc = run_cli("check", str(ledger), "--today", "2026-10-15", "--format", "json")
        assert proc.returncode == 2
        assert code in {f["code"] for f in json.loads(proc.stdout)["findings"]}

    @pytest.mark.parametrize("command", ["check", "report"])
    @pytest.mark.parametrize("target", ["toml", "inventory"])
    def test_non_utf8_input_has_clear_error(self, tmp_path, command, target):
        ledger = tmp_path / "quarantine.toml"
        ledger.write_text(VALID_ENTRY_TOML, encoding="utf-8")
        args = [command, str(ledger), "--today", "2026-10-15"]
        if target == "toml":
            ledger.write_bytes(b"#\x80")
        else:
            inventory = tmp_path / "tests.json"
            inventory.write_bytes(b'["test_\x80"]')
            args.extend(["--inventory", str(inventory)])
        proc = run_cli(*args)
        assert proc.returncode == 2
        assert "UTF-8" in proc.stderr
        assert "Traceback" not in proc.stderr

    def test_pytest_node_id_is_accepted(self, tmp_path):
        ledger = tmp_path / "quarantine.toml"
        ledger.write_text(
            VALID_ENTRY_TOML.replace("test1", "tests/test_auth.py::test_login"), encoding="utf-8"
        )
        proc = run_cli("check", str(ledger), "--today", "2026-10-15")
        assert proc.returncode == 0, proc.stdout + proc.stderr

    @pytest.mark.parametrize("command", ["check", "report"])
    @pytest.mark.parametrize("target", ["created", "today"])
    def test_unpadded_date_is_rejected(self, tmp_path, command, target):
        ledger = tmp_path / "quarantine.toml"
        content = (
            VALID_ENTRY_TOML.replace("2026-10-01", "2026-1-2")
            if target == "created"
            else VALID_ENTRY_TOML
        )
        ledger.write_text(content, encoding="utf-8")
        proc = run_cli(
            command, str(ledger), "--today", "2026-10-5" if target == "today" else "2026-10-15"
        )
        assert proc.returncode == 2
        assert "YYYY-MM-DD" in proc.stderr

    def test_version_contract(self):
        proc = run_cli("--version")
        assert proc.returncode == 0
        assert "quarantine-ledger 0.1.0" in proc.stdout

    @pytest.mark.parametrize("command", ["check", "report"])
    def test_finding_json_keeps_entry_index(self, tmp_path, command):
        ledger = tmp_path / "quarantine.toml"
        ledger.write_text(VALID_ENTRY_TOML.replace("2026-11-01", "2026-10-10"), encoding="utf-8")
        proc = run_cli(command, str(ledger), "--today", "2026-10-15", "--format", "json")
        assert proc.returncode == (1 if command == "check" else 0)
        findings = json.loads(proc.stdout)["findings"]
        assert findings
        assert all(f["entry_index"] == 0 for f in findings)
