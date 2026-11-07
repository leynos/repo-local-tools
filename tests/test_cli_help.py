"""CLI help coverage for repo-local-tools."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_top_level_help_explains_registry_and_command_groups() -> None:
    """Assert that top-level help names the data registry and command groups."""
    result = run_help("--help")

    assert result.returncode == 0
    assert "$XDG_DATA_HOME/repo-local-tools" in result.stdout
    assert "load" in result.stdout
    assert "mcp" in result.stdout
    assert "skill" in result.stdout


def test_load_help_explains_supported_sources() -> None:
    """Assert that load help lists the supported source formats and location."""
    result = run_help("load", "--help")

    assert result.returncode == 0
    assert "SKILL.md" in result.stdout
    assert ".skill" in result.stdout
    assert "mcp.json" in result.stdout
    assert "current directory" in result.stdout


def test_mcp_help_explains_supported_clients_and_registry_path() -> None:
    """Assert that mcp help names the supported clients and the registry path."""
    result = run_help("mcp", "--help")

    assert result.returncode == 0
    assert "Model Context Protocol" in result.stdout
    assert "mcp-servers" in result.stdout
    assert "Claude" in result.stdout
    assert "Cursor" in result.stdout


def test_skill_install_help_explains_archive_form() -> None:
    """Assert that skill install help documents the archive form of the command."""
    result = run_help("skill", "install", "--help")

    assert result.returncode == 0
    assert ".skill" in result.stdout
    assert "absolute path" in result.stdout
    assert "top-level skill directory" in result.stdout


def run_help(*arguments: str) -> subprocess.CompletedProcess[str]:
    """Run the repo_local_tools CLI with the given arguments and capture output."""
    return subprocess.run(
        [sys.executable, "-m", "repo_local_tools.cli", *arguments],
        cwd=Path.cwd(),
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
