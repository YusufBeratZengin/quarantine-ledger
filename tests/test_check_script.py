"""Regression tests for the lint gate that silently checked zero files.

Ruff skips files its gitignore support considers ignored. This project was once
checked out inside a parent repository whose ``.git/info/exclude`` is ``*``,
so ``ruff check src tests`` reported "No Python files found" and still exited 0:
the lint step of scripts/check.sh became a no-op that looked green.
"""

import shutil
import subprocess
import tomllib
from pathlib import Path

import pytest
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name
from packaging.version import Version

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUFF = shutil.which("ruff")
GIT = shutil.which("git")

pytestmark = pytest.mark.integration


def _run(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, capture_output=True, text=True, check=False)


@pytest.mark.skipif(RUFF is None, reason="ruff is not installed")
@pytest.mark.skipif(GIT is None, reason="git is not installed")
def test_gitignored_checkout_is_still_discovered(tmp_path):
    project = tmp_path / "ignored-checkout"
    (project / "src").mkdir(parents=True)
    (project / "src" / "sample.py").write_text('"""Sample."""\n\nVALUE = 1\n', encoding="utf-8")

    _run([GIT or "git", "init", "-q"], project)
    (project / ".git" / "info" / "exclude").write_text("*\n", encoding="utf-8")

    respecting = _run([RUFF or "ruff", "check", "--show-files", "src"], project)
    assert respecting.stdout.strip() == "", "precondition: gitignore hides every file"

    explicit = _run(
        [RUFF or "ruff", "check", "--no-respect-gitignore", "--show-files", "src"], project
    )
    assert "sample.py" in explicit.stdout


@pytest.mark.skipif(RUFF is None, reason="ruff is not installed")
def test_check_script_discovery_sees_this_project():
    result = _run(
        [RUFF or "ruff", "check", "--no-respect-gitignore", "--show-files", "src", "tests"],
        PROJECT_ROOT,
    )
    files = [line.strip() for line in result.stdout.splitlines() if line.strip()]

    assert result.returncode == 0, result.stderr
    assert any(path.endswith("cli.py") for path in files)
    assert any(path.endswith("test_cli.py") for path in files)
    assert len(files) >= 10


def test_dev_lockfile_matches_pyproject_and_ci_workflow():
    """requirements-dev.lock must pin pyproject dev deps and be used by CI."""
    pyproject = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    dev_specs = [Requirement(raw) for raw in pyproject["project"]["optional-dependencies"]["dev"]]

    lock_lines = [
        line.strip()
        for line in (PROJECT_ROOT / "requirements-dev.lock")
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    assert lock_lines, "requirements-dev.lock must not be empty"

    locked_versions: dict[str, Version] = {}
    for line in lock_lines:
        req = Requirement(line)
        specs = list(req.specifier)
        assert len(specs) == 1 and specs[0].operator == "==", (
            f"lockfile entry must use exact == pin: {line}"
        )
        locked_versions[canonicalize_name(req.name)] = Version(specs[0].version)

    for dev_req in dev_specs:
        key = canonicalize_name(dev_req.name)
        assert key in locked_versions, f"{dev_req.name} missing from requirements-dev.lock"
        assert dev_req.specifier.contains(locked_versions[key], prereleases=True), (
            f"{dev_req.name}=={locked_versions[key]} does not satisfy {dev_req.specifier}"
        )

    ci_yaml = (PROJECT_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "requirements-dev.lock" in ci_yaml


def test_dev_dependencies_keep_upper_bounds():
    config = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    for spec in config["project"]["optional-dependencies"]["dev"]:
        assert any(bound.operator == "<" for bound in Requirement(spec).specifier), spec


@pytest.mark.skipif(RUFF is None or GIT is None, reason="ruff and git required")
def test_check_script_rejects_ignored_unused_import(tmp_path):
    project = tmp_path / "ignored-checkout"
    (project / "src").mkdir(parents=True)
    (project / "tests").mkdir()
    (project / "scripts").mkdir()
    shutil.copyfile(PROJECT_ROOT / "scripts" / "check.sh", project / "scripts" / "check.sh")
    (project / "src" / "sample.py").write_text("import math\n", encoding="utf-8")
    _run([GIT or "git", "init", "-q"], project)
    (project / ".git" / "info" / "exclude").write_text("*\n", encoding="utf-8")
    # Later stages are deliberately successful: lint must itself reject F401.
    tools = project / "tools"
    tools.mkdir()
    for name in ("mypy", "python"):
        (tools / name).write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
        (tools / name).chmod(0o755)
    import os

    env = dict(os.environ)
    env["PATH"] = str(tools) + os.pathsep + env["PATH"]
    env.pop("QUARANTINE_LEDGER_RESPECT_GITIGNORE", None)
    result = subprocess.run(
        ["bash", "scripts/check.sh"], cwd=project, env=env, capture_output=True, text=True
    )
    assert result.returncode == 1, result.stdout + result.stderr
    assert "F401" in result.stdout + result.stderr
