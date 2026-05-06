"""Shared pytest helpers for repo-local-tools tests."""

from __future__ import annotations

import subprocess  # noqa: S404
import typing as typ

if typ.TYPE_CHECKING:
    from pathlib import Path

GIT_EXECUTABLE = "git"


def initialize_git(repository: Path) -> None:
    """Initialise a test Git repository with deterministic author metadata."""
    subprocess.run(  # noqa: S603
        [GIT_EXECUTABLE, "init"], cwd=repository, check=True, capture_output=True
    )
    subprocess.run(  # noqa: S603
        [GIT_EXECUTABLE, "config", "user.email", "tests@example.invalid"],
        cwd=repository,
        check=True,
        capture_output=True,
    )
    subprocess.run(  # noqa: S603
        [GIT_EXECUTABLE, "config", "user.name", "Repo Local Tools Tests"],
        cwd=repository,
        check=True,
        capture_output=True,
    )


def write_mcp_definition(xdg_data_home: Path, name: str) -> None:
    """Write a minimal shared MCP definition for tests."""
    registry = xdg_data_home / "repo-local-tools" / "mcp-servers"
    registry.mkdir(parents=True, exist_ok=True)
    (registry / f"{name}.toml").write_text(
        f'name = "{name}"\ncommand = "python"\nargs = ["-m", "example"]\n',
    )


def write_skill_definition(
    xdg_data_home: Path,
    name: str,
    content: str = "Use evidence.\n",
) -> None:
    """Write a minimal shared skill definition for tests."""
    skill = xdg_data_home / "repo-local-tools" / "skills" / name
    skill.mkdir(parents=True, exist_ok=True)
    (skill / "SKILL.md").write_text(content)
