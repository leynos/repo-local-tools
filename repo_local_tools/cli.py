"""Command-line interface for repo-local-tools."""

from __future__ import annotations

import sys
import typing as typ
from pathlib import Path

import cyclopts

from repo_local_tools.agent_tools.errors import AgentToolsError
from repo_local_tools.agent_tools.git_ops import commit_managed_tool
from repo_local_tools.agent_tools.install import (
    install_mcp,
    install_skill,
    update_mcps,
    update_skills,
)
from repo_local_tools.agent_tools.load import LoadResult, load_path
from repo_local_tools.agent_tools.paths import current_repository

if typ.TYPE_CHECKING:
    import collections.abc as cabc

COMMAND_GROUPS = ("mcp", "skill")
ToolName = typ.Annotated[
    str,
    cyclopts.Parameter(
        help=(
            "Name of the shared registry entry. For skill install, an absolute "
            "path ending in .skill may be used instead."
        ),
    ),
]
OptionalToolName = typ.Annotated[
    str | None,
    cyclopts.Parameter(
        help="Optional managed item name. Omit it to update every managed item.",
    ),
]
OptionalLoadPath = typ.Annotated[
    str | None,
    cyclopts.Parameter(
        help=(
            "Optional path to a SKILL.md file, .skill archive, MCP JSON file, "
            "or directory. Omit it to scan the current directory."
        ),
    ),
]

app = cyclopts.App(
    name="repo-local-tools",
    help="Install, update, and commit repository-local agent tool files.",
    usage="repo-local-tools COMMAND [ARGS] [OPTIONS]",
    help_prologue=(
        "repo-local-tools reads shared MCP server definitions and skill "
        "repositories from $XDG_DATA_HOME/repo-local-tools, renders them into "
        "the current Git repository for supported agent clients, records "
        "managed ownership metadata, and updates .gitignore for generated "
        "paths."
    ),
    help_epilogue=(
        "Run commands from the target repository root. Use `repo-local-tools "
        "mcp --help` or `repo-local-tools skill --help` for workflow-specific "
        "commands."
    ),
)
mcp_app = app.command(
    cyclopts.App(
        name="mcp",
        help="Manage Model Context Protocol server configuration.",
        usage="repo-local-tools mcp COMMAND [ARGS] [OPTIONS]",
        help_prologue=(
            "MCP commands read TOML definitions from "
            "$XDG_DATA_HOME/repo-local-tools/mcp-servers and render repo-local "
            "client configuration for Claude, Codex, Factory Droid, and Cursor."
        ),
    ),
)
skill_app = app.command(
    cyclopts.App(
        name="skill",
        help="Manage agent skill directories and .skill archives.",
        usage="repo-local-tools skill COMMAND [ARGS] [OPTIONS]",
        help_prologue=(
            "Skill commands read shared skill repositories from "
            "$XDG_DATA_HOME/repo-local-tools/skills, or install an absolute "
            "path to an Anthropic .skill archive."
        ),
    ),
)


@app.command(name="load")
def load(source: OptionalLoadPath = None) -> None:
    """Load local skills and MCP server JSON into the shared registry.

    Without an argument, the current directory is scanned for `SKILL.md`,
    `mcp.json`, `mcpServers.json`, `.skill` bundles, and `skill` or `skills`
    subdirectories. With an argument, the path is loaded directly when it is a
    supported file, or scanned with the same directory rules otherwise.
    """
    _run_or_exit(
        lambda: _print_load_results(load_path(_load_source(source), Path.cwd(), None))
    )


@mcp_app.command(name="install")
def mcp_install(name: ToolName) -> None:
    """Install one MCP server from the shared registry.

    The definition is loaded from
    `$XDG_DATA_HOME/repo-local-tools/mcp-servers/<name>.toml`, rendered into
    each supported repo-local client configuration, recorded in the
    managed-tool manifest, and added to `.gitignore` where required.
    """
    _run_or_exit(lambda: install_mcp(name, current_repository(), None))


@mcp_app.command(name="update")
def mcp_update(name: OptionalToolName = None) -> None:
    """Update one or all managed MCP servers.

    With `name`, only that managed MCP server is refreshed from its shared
    definition. Without `name`, every managed MCP server recorded in
    `.repo-local-tools/managed-tools.json` is refreshed.
    """
    _run_or_exit(lambda: update_mcps(name, current_repository(), None))


@mcp_app.command(name="commit")
def mcp_commit(name: ToolName) -> None:
    """Commit one managed MCP server.

    The command stages only the named MCP server's managed files, the manifest,
    and relevant `.gitignore` entries. It refuses to commit when unrelated
    repository changes are present.
    """
    _run_or_exit(lambda: commit_managed_tool(current_repository(), "mcps", name))


@skill_app.command(name="install")
def skill_install(name: ToolName) -> None:
    """Install one skill from the shared registry or a `.skill` archive.

    Registry installs read
    `$XDG_DATA_HOME/repo-local-tools/skills/<name>`. Archive installs require
    an absolute path ending in `.skill`; the archive must contain exactly one
    top-level skill directory.
    """
    _run_or_exit(lambda: install_skill(name, current_repository(), None))


@skill_app.command(name="update")
def skill_update(name: OptionalToolName = None) -> None:
    """Update one or all managed skills.

    With `name`, only that managed skill is refreshed. Without `name`, every
    managed skill recorded in `.repo-local-tools/managed-tools.json` is
    refreshed.
    """
    _run_or_exit(lambda: update_skills(name, current_repository(), None))


@skill_app.command(name="commit")
def skill_commit(name: ToolName) -> None:
    """Commit one managed skill.

    The command stages only the named skill's managed files, the manifest, and
    relevant `.gitignore` entries. It refuses to commit when unrelated
    repository changes are present.
    """
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


def _load_source(source: str | None) -> Path | None:
    if source is None:
        return None
    return Path(source)


def _print_load_results(results: list[LoadResult]) -> None:
    for result in results:
        print(f"Loaded {result.kind} {result.name} to {result.path}")


if __name__ == "__main__":
    main()
