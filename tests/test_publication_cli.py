"""Tests for CLI module."""

import json
import tempfile
from pathlib import Path

import pytest

from quarantine_ledger import __version__
from quarantine_ledger.cli import main


def create_temp_file(content: str, suffix: str) -> Path:
    with tempfile.NamedTemporaryFile(mode="w", suffix=suffix, delete=False) as f:
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

    def test_check_mixed_expired_and_budget_exits_1(self, tmp_path, capsys):
        toml_content = """
[policy]
max_total_entries = 1
max_entries_per_team = 1

[[entries]]
id = "test_expired"
owner_team = "team-a"
issue = "https://github.com/example/issues/1"
reason = "Reason"
created = "2026-10-01"
expires = "2026-10-10"

[[entries]]
id = "test_active"
owner_team = "team-a"
issue = "https://github.com/example/issues/2"
reason = "Reason"
created = "2026-10-01"
expires = "2026-11-01"
"""
        toml_path = tmp_path / "quarantine.toml"
        toml_path.write_text(toml_content, encoding="utf-8")

        exit_code = main([
            "check",
            str(toml_path),
            "--today",
            "2026-10-15",
            "--format",
            "json",
        ])

        payload = json.loads(capsys.readouterr().out)
        codes = {f["code"] for f in payload["findings"]}
        assert exit_code == 1
        assert payload["exit_code"] == 1
        assert {"EXPIRED", "BUDGET_EXCEEDED_TOTAL", "BUDGET_EXCEEDED_TEAM"} <= codes


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
    def test_version_flag(self, capsys):
        with pytest.raises(SystemExit) as excinfo:
            main(["--version"])
        assert excinfo.value.code == 0
        assert __version__ in capsys.readouterr().out

    def test_invalid_toml(self):
        toml_content = "invalid toml [[["
        toml_path = create_temp_file(toml_content, ".toml")
        try:
            exit_code = main(["check", str(toml_path)])
            assert exit_code == 2
        finally:
            toml_path.unlink()

    @pytest.mark.parametrize("command", ["check", "report"])
    def test_invalid_utf8_toml_exits_2(self, command, tmp_path, capsys):
        toml_path = tmp_path / "invalid_utf8.toml"
        toml_path.write_bytes(b"\xff\xfe[[entries]]\n")

        exit_code = main([command, str(toml_path), "--today", "2026-10-15"])

        captured = capsys.readouterr()
        assert exit_code == 2
        assert "UTF-8" in captured.err
        assert "Traceback" not in captured.err

    def test_missing_file(self):
        exit_code = main(["check", "/nonexistent/path.toml"])
        assert exit_code == 2

    def test_unpadded_entry_date_exits_2(self, capsys):
        content = """
[[entries]]
id = "test1"
owner_team = "team-a"
issue = "https://github.com/example/issues/1"
reason = "Reason"
created = "2026-1-2"
expires = "2026-02-01"
"""
        toml_path = create_temp_file(content, ".toml")
        try:
            exit_code = main(["check", str(toml_path), "--today", "2026-02-01"])
        finally:
            toml_path.unlink()

        captured = capsys.readouterr()
        assert exit_code == 2
        assert "expected YYYY-MM-DD" in captured.err
        assert "Traceback" not in captured.err

    def test_no_command(self):
        exit_code = main([])
        assert exit_code == 2


VALID_TOML = """
[[entries]]
id = "test1"
owner_team = "team-a"
issue = "https://github.com/example/issues/1"
reason = "Reason"
created = "2026-10-01"
expires = "2026-11-01"
"""


class TestInvalidToday:
    """--today used to be parsed outside the error handling, so a bad value
    escaped as a ValueError traceback instead of exit code 2."""

    @pytest.mark.parametrize("command", ["check", "report"])
    def test_invalid_today_is_usage_error(self, command, capsys):
        toml_path = create_temp_file(VALID_TOML, ".toml")
        try:
            exit_code = main([command, str(toml_path), "--today", "2026-13-01"])
        finally:
            toml_path.unlink()

        captured = capsys.readouterr()
        assert exit_code == 2
        assert "--today" in captured.err
        assert "expected YYYY-MM-DD" in captured.err
        assert "Traceback" not in captured.err

    @pytest.mark.parametrize("bad_today", ["2026-1-2", "2026-01-2", "2026-1-02", "20260102"])
    def test_unpadded_today_is_usage_error(self, bad_today, capsys):
        toml_path = create_temp_file(VALID_TOML, ".toml")
        try:
            exit_code = main(["check", str(toml_path), "--today", bad_today])
        finally:
            toml_path.unlink()

        captured = capsys.readouterr()
        assert exit_code == 2
        assert "--today" in captured.err
        assert "expected YYYY-MM-DD" in captured.err
        assert "Traceback" not in captured.err

    def test_empty_today_is_usage_error(self, capsys):
        toml_path = create_temp_file(VALID_TOML, ".toml")
        try:
            exit_code = main(["check", str(toml_path), "--today", ""])
        finally:
            toml_path.unlink()

        assert exit_code == 2
        assert "--today" in capsys.readouterr().err


class TestPolicyTypeErrorsAtCliLevel:
    def test_policy_scalar_exits_2(self, capsys):
        toml_path = create_temp_file('policy = "wrong"\n', ".toml")
        try:
            exit_code = main(["check", str(toml_path)])
        finally:
            toml_path.unlink()

        captured = capsys.readouterr()
        assert exit_code == 2
        assert "policy: must be a table, got str" in captured.err

    def test_all_errors_are_listed(self, capsys):
        content = """
[policy]
max_age_days = "30"

[[entries]]
id = "test1"
owner_team = "a@example.com"
issue = "not-a-url"
reason = " "
created = "2026-10-01"
expires = "2026-11-01"
"""
        toml_path = create_temp_file(content, ".toml")
        try:
            exit_code = main(["check", str(toml_path), "--today", "2026-10-15", "--format", "json"])
        finally:
            toml_path.unlink()

        assert exit_code == 2
        assert "max_age_days: must be an integer" in capsys.readouterr().err


class TestRootKeyAtCliLevel:
    """A root-key typo must be a usage error, not a silently empty ledger."""

    def test_entries_typo_exits_2(self, capsys):
        content = """
[[entry]]
id = "test1"
owner_team = "team-a"
issue = "https://github.com/example/issues/1"
reason = "Reason"
created = "2026-10-01"
expires = "2026-11-01"
"""
        toml_path = create_temp_file(content, ".toml")
        try:
            exit_code = main(["check", str(toml_path), "--today", "2026-10-15"])
        finally:
            toml_path.unlink()

        captured = capsys.readouterr()
        assert exit_code == 2
        assert "root: unknown key 'entry'" in captured.err
        assert "[[entries]]" in captured.err
        assert "Traceback" not in captured.err


class TestDemoSafety:
    def test_refuses_to_overwrite_existing_files(self, tmp_path, capsys):
        demo_dir = tmp_path / "demo"
        assert main(["demo", "--dir", str(demo_dir)]) == 0
        capsys.readouterr()

        ledger = demo_dir / "quarantine.toml"
        user_content = "# edited by the user\n"
        ledger.write_text(user_content, encoding="utf-8")

        exit_code = main(["demo", "--dir", str(demo_dir)])

        captured = capsys.readouterr()
        assert exit_code == 2
        assert "refusing to overwrite" in captured.err
        assert ledger.read_text(encoding="utf-8") == user_content

    def test_refuses_to_overwrite_existing_temp_files(self, tmp_path, capsys):
        demo_dir = tmp_path / "demo"
        demo_dir.mkdir(parents=True, exist_ok=True)
        temp_file = demo_dir / ".quarantine.toml.tmp"
        user_temp_content = "user temporary data\n"
        temp_file.write_text(user_temp_content, encoding="utf-8")

        exit_code = main(["demo", "--dir", str(demo_dir)])

        captured = capsys.readouterr()
        assert exit_code == 2
        assert "refusing to overwrite existing file(s)" in captured.err
        assert ".quarantine.toml.tmp" in captured.err
        assert temp_file.read_text(encoding="utf-8") == user_temp_content
        assert not (demo_dir / "quarantine.toml").exists()

    def test_exclusive_temp_creation_leaves_preexisting_temp_file_untouched(self, tmp_path):
        from quarantine_ledger.cli import _write_demo_files

        demo_dir = tmp_path / "demo"
        demo_dir.mkdir(parents=True, exist_ok=True)
        temp_file = demo_dir / ".quarantine.toml.tmp"
        temp_file.write_text("protected content\n", encoding="utf-8")

        with pytest.raises(OSError):
            _write_demo_files(demo_dir, created_dir=False)

        assert temp_file.exists()
        assert temp_file.read_text(encoding="utf-8") == "protected content\n"

    def test_refuses_when_dir_is_a_file(self, tmp_path, capsys):
        target = tmp_path / "not-a-dir"
        target.write_text("keep me", encoding="utf-8")

        exit_code = main(["demo", "--dir", str(target)])

        assert exit_code == 2
        assert "is not a directory" in capsys.readouterr().err
        assert target.read_text(encoding="utf-8") == "keep me"

    def test_partial_write_is_rolled_back(self, tmp_path, capsys, monkeypatch):
        """A failure halfway through ``demo`` must not leave a partial project."""
        from quarantine_ledger import cli

        demo_dir = tmp_path / "demo"
        real_move = cli._move_without_overwrite
        calls = {"count": 0}

        def failing_move(source, target):
            calls["count"] += 1
            if calls["count"] == 2:
                raise OSError("disk full (simulated)")
            return real_move(source, target)

        monkeypatch.setattr(cli, "_move_without_overwrite", failing_move)

        exit_code = main(["demo", "--dir", str(demo_dir)])

        captured = capsys.readouterr()
        assert exit_code == 2
        assert "could not create demo" in captured.err
        assert "removed" in captured.err
        assert calls["count"] == 2
        assert not demo_dir.exists() or list(demo_dir.iterdir()) == []

    def test_demo_race_condition_does_not_overwrite_target_created_during_staging(
        self, tmp_path, capsys, monkeypatch
    ):
        """A race condition where target is created during staging must not overwrite it."""
        from quarantine_ledger import cli

        demo_dir = tmp_path / "demo"
        target_file = demo_dir / "quarantine.toml"
        user_precious_data = "precious user data created in race condition\n"

        real_move = cli._move_without_overwrite

        def race_condition_move(source, target):
            # Target is created just before the move happens
            target_file.write_text(user_precious_data, encoding="utf-8")
            return real_move(source, target)

        monkeypatch.setattr(cli, "_move_without_overwrite", race_condition_move)

        exit_code = main(["demo", "--dir", str(demo_dir)])

        captured = capsys.readouterr()
        assert exit_code == 2
        assert "could not create demo" in captured.err
        assert target_file.read_text(encoding="utf-8") == user_precious_data

    def test_move_without_overwrite_unit(self, tmp_path):
        """_move_without_overwrite moves source when target does not exist,
        and raises FileExistsError without touching target when target exists."""
        from quarantine_ledger.cli import _move_without_overwrite

        source = tmp_path / "src.txt"
        target = tmp_path / "dst.txt"
        source.write_text("source data", encoding="utf-8")

        # 1. Normal atomic move
        _move_without_overwrite(source, target)
        assert not source.exists()
        assert target.read_text(encoding="utf-8") == "source data"

        # 2. Race condition / target already exists
        new_source = tmp_path / "new_src.txt"
        new_source.write_text("new source data", encoding="utf-8")

        with pytest.raises(FileExistsError):
            _move_without_overwrite(new_source, target)

        assert new_source.exists()
        assert target.read_text(encoding="utf-8") == "source data"  # untouched!

    def test_move_without_overwrite_fallback_on_unsupported_link(self, tmp_path, monkeypatch):
        """When hard links raise an unsupported OSError, fallback to rename succeeds on Windows
        or raises the original OSError on POSIX."""
        from quarantine_ledger.cli import _move_without_overwrite

        source = tmp_path / "fallback_src.txt"
        target = tmp_path / "fallback_dst.txt"
        source.write_text("fallback payload", encoding="utf-8")

        def failing_hardlink(self, target_path):
            raise OSError("hardlink not supported on this filesystem")

        monkeypatch.setattr(Path, "hardlink_to", failing_hardlink)

        import os

        if os.name == "nt":
            _move_without_overwrite(source, target)
            assert not source.exists()
            assert target.read_text(encoding="utf-8") == "fallback payload"
        else:
            with pytest.raises(OSError, match="hardlink not supported"):
                _move_without_overwrite(source, target)

    def test_generated_demo_fails_the_gate(self, tmp_path, capsys):
        demo_dir = tmp_path / "demo"
        assert main(["demo", "--dir", str(demo_dir)]) == 0
        capsys.readouterr()

        exit_code = main([
            "check",
            str(demo_dir / "quarantine.toml"),
            "--inventory",
            str(demo_dir / "tests.json"),
            "--today",
            "2026-11-02",
        ])

        output = capsys.readouterr().out
        assert exit_code == 1
        assert "EXPIRED" in output
        assert "test_expired_example" in output


class TestEntryFormatAtCliLevel:
    """The id and issue rules must hold on the real CLI path.

    ``QuarantineEntry.validate_id_format`` used to be dead code as far as the
    CLI was concerned and the issue check only looked at the scheme prefix, so
    ``id = "test_*"`` and ``issue = "https://"`` both passed the gate.
    """

    def test_wildcard_id_is_rejected(self, capsys):
        toml_path = create_temp_file(VALID_TOML.replace('id = "test1"', 'id = "test_*"'), ".toml")
        try:
            exit_code = main(["check", str(toml_path), "--today", "2026-10-15"])
        finally:
            toml_path.unlink()

        output = capsys.readouterr().out
        assert exit_code == 2
        assert "INVALID_ID" in output
        assert "wildcard" in output

    def test_single_colon_id_is_rejected(self, tmp_path, capsys):
        ledger_path = tmp_path / "quarantine.toml"
        ledger_path.write_text(
            VALID_TOML.replace('id = "test1"', 'id = "tests/test_auth.py:test_timeout"'),
            encoding="utf-8",
        )

        exit_code = main(["check", str(ledger_path), "--today", "2026-10-15"])

        output = capsys.readouterr().out
        assert exit_code == 2
        assert "INVALID_ID" in output
        assert "invalid characters" in output

    @pytest.mark.parametrize(
        "url",
        [
            "https://",
            "http:///issues/1",
            "https://?issue=1",
            "https://exa mple.com/issues/1",
        ],
    )
    def test_issue_url_without_host_is_rejected(self, url, capsys):
        content = VALID_TOML.replace(
            'issue = "https://github.com/example/issues/1"', f'issue = "{url}"'
        )
        toml_path = create_temp_file(content, ".toml")
        try:
            exit_code = main(["check", str(toml_path), "--today", "2026-10-15"])
        finally:
            toml_path.unlink()

        output = capsys.readouterr().out
        assert exit_code == 2
        assert "INVALID_ISSUE_URL" in output


class TestInventoryErrorsAtCliLevel:
    """Inventory I/O, encoding, and schema errors must return exit code 2 without a traceback."""

    @pytest.mark.parametrize("command", ["check", "report"])
    @pytest.mark.parametrize("bad_bytes", [b"\xff\xfe[]", b'["test_\x80"]'])
    def test_invalid_utf8_inventory_exits_2(self, command, bad_bytes, tmp_path, capsys):
        ledger_path = tmp_path / "quarantine.toml"
        ledger_path.write_text(VALID_TOML, encoding="utf-8")
        inv_path = tmp_path / "tests.json"
        inv_path.write_bytes(bad_bytes)

        exit_code = main([
            command,
            str(ledger_path),
            "--inventory",
            str(inv_path),
            "--today",
            "2026-10-15",
        ])

        captured = capsys.readouterr()
        assert exit_code == 2
        assert "Failed to load inventory" in captured.err
        assert "UTF-8" in captured.err
        assert "Traceback" not in captured.err

    def test_missing_inventory_exits_2(self, tmp_path, capsys):
        ledger_path = tmp_path / "quarantine.toml"
        ledger_path.write_text(VALID_TOML, encoding="utf-8")
        missing_inv = tmp_path / "does_not_exist.json"

        exit_code = main([
            "check",
            str(ledger_path),
            "--inventory",
            str(missing_inv),
            "--today",
            "2026-10-15",
        ])

        captured = capsys.readouterr()
        assert exit_code == 2
        assert "Failed to load inventory" in captured.err
        assert "Traceback" not in captured.err
