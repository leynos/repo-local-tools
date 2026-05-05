from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from conftest import initialize_git, write_mcp_definition, write_skill_definition
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

    result = subprocess.run(  # noqa: S603, RUF100
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

    with pytest.raises(GitError, match="unknown managed MCP server"):
        commit_managed_tool(repository, "mcps", "does-not-exist")


def test_commit_managed_tool_commits_skill_paths(tmp_path: Path) -> None:
    repository = tmp_path / "repo"
    xdg_data_home = tmp_path / "xdg"
    repository.mkdir()
    initialize_git(repository)
    write_skill_definition(xdg_data_home, "greeter")
    install_skill("greeter", repository, xdg_data_home)

    commit_managed_tool(repository, "skills", "greeter")

    result = subprocess.run(  # noqa: S603, RUF100
        ["git", "log", "-1", "--pretty=%s"],
        cwd=repository,
        check=True,
        capture_output=True,
        text=True,
    )
    assert result.stdout.strip() == "Install skill greeter"
