from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from repo_local_tools.agent_tools.git_ops import GitError, commit_managed_tool
from repo_local_tools.agent_tools.install import install_mcp, install_skill


def test_commit_managed_tool_refuses_unrelated_changes(tmp_path: Path) -> None:
    repository = tmp_path / "repo"
    xdg_data_home = tmp_path / "xdg"
    repository.mkdir()
    initialize_git(repository)
    write_mcp_definition(xdg_data_home, "echo")
    install_mcp("echo", repository, xdg_data_home)
    (repository / "unrelated.txt").write_text("user work\n")

    with pytest.raises(GitError, match="unrelated"):
        commit_managed_tool(repository, "mcps", "echo")


def test_commit_managed_tool_commits_owned_paths(tmp_path: Path) -> None:
    repository = tmp_path / "repo"
    xdg_data_home = tmp_path / "xdg"
    repository.mkdir()
    initialize_git(repository)
    write_mcp_definition(xdg_data_home, "echo")
    install_mcp("echo", repository, xdg_data_home)

    commit_managed_tool(repository, "mcps", "echo")

    result = subprocess.run(
        ["git", "log", "-1", "--pretty=%s"],
        cwd=repository,
        check=True,
        capture_output=True,
        text=True,
    )
    assert result.stdout.strip() == "Install MCP server echo"


def test_commit_managed_tool_no_managed_changes_to_commit(tmp_path: Path) -> None:
    repository = tmp_path / "repo"
    xdg_data_home = tmp_path / "xdg"
    repository.mkdir()
    initialize_git(repository)
    write_mcp_definition(xdg_data_home, "echo")
    install_mcp("echo", repository, xdg_data_home)
    commit_managed_tool(repository, "mcps", "echo")

    with pytest.raises(GitError, match="no managed changes to commit"):
        commit_managed_tool(repository, "mcps", "echo")


def test_commit_managed_tool_unknown_managed_tool_raises(tmp_path: Path) -> None:
    repository = tmp_path / "repo"
    repository.mkdir()
    initialize_git(repository)

    with pytest.raises(GitError, match="unknown managed tool"):
        commit_managed_tool(repository, "mcps", "does-not-exist")


def test_commit_managed_tool_commits_skill_paths(tmp_path: Path) -> None:
    repository = tmp_path / "repo"
    xdg_data_home = tmp_path / "xdg"
    repository.mkdir()
    initialize_git(repository)
    write_skill_definition(xdg_data_home, "greeter")
    install_skill("greeter", repository, xdg_data_home)

    commit_managed_tool(repository, "skills", "greeter")

    result = subprocess.run(
        ["git", "log", "-1", "--pretty=%s"],
        cwd=repository,
        check=True,
        capture_output=True,
        text=True,
    )
    assert result.stdout.strip() == "Install skill greeter"


def initialize_git(repository: Path) -> None:
    subprocess.run(["git", "init"], cwd=repository, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "tests@example.invalid"],
        cwd=repository,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Repo Local Tools Tests"],
        cwd=repository,
        check=True,
        capture_output=True,
    )


def write_mcp_definition(xdg_data_home: Path, name: str) -> None:
    registry = xdg_data_home / "repo-local-tools" / "mcp-servers"
    registry.mkdir(parents=True)
    (registry / f"{name}.toml").write_text(
        f'name = "{name}"\ncommand = "python"\nargs = ["-m", "example"]\n',
    )


def write_skill_definition(xdg_data_home: Path, name: str) -> None:
    skill = xdg_data_home / "repo-local-tools" / "skills" / name
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("Say hello.\n")
