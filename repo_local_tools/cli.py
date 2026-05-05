"""Command-line interface for repo-local-tools."""

from __future__ import annotations

import sys
import typing as typ

import cyclopts

from repo_local_tools.agent_tools.errors import AgentToolsError
from repo_local_tools.agent_tools.git_ops import commit_managed_tool
from repo_local_tools.agent_tools.install import (
    install_mcp,
    install_skill,
    update_mcps,
    update_skills,
)
from repo_local_tools.agent_tools.paths import current_repository

if typ.TYPE_CHECKING:
    import collections.abc as cabc

COMMAND_GROUPS = ("mcp", "skill")

app = cyclopts.App(name="repo-local-tools")
mcp_app = app.command(cyclopts.App(name="mcp"))
skill_app = app.command(cyclopts.App(name="skill"))


@mcp_app.command(name="install")
def mcp_install(name: str) -> None:
    """Install one MCP server in the current repository."""
    _run_or_exit(lambda: install_mcp(name, current_repository(), None))


@mcp_app.command(name="update")
def mcp_update(name: str | None = None) -> None:
    """Update one or all managed MCP servers in the current repository."""
    _run_or_exit(lambda: update_mcps(name, current_repository(), None))


@mcp_app.command(name="commit")
def mcp_commit(name: str) -> None:
    """Commit one managed MCP server in the current repository."""
    _run_or_exit(lambda: commit_managed_tool(current_repository(), "mcps", name))


@skill_app.command(name="install")
def skill_install(name: str) -> None:
    """Install one skill in the current repository."""
    _run_or_exit(lambda: install_skill(name, current_repository(), None))


@skill_app.command(name="update")
def skill_update(name: str | None = None) -> None:
    """Update one or all managed skills in the current repository."""
    _run_or_exit(lambda: update_skills(name, current_repository(), None))


@skill_app.command(name="commit")
def skill_commit(name: str) -> None:
    """Commit one managed skill in the current repository."""
    _run_or_exit(lambda: commit_managed_tool(current_repository(), "skills", name))


def main() -> None:
    """Run the repo-local-tools command-line interface."""
    app()


def _run_or_exit(action: cabc.Callable[[], object]) -> None:
    try:
        action()
    except AgentToolsError as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(1) from error


if __name__ == "__main__":
    main()
