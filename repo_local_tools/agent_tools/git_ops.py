"""Scoped Git operations for managed agent tools."""

from __future__ import annotations

import shutil
import subprocess  # ruff: ignore[suspicious-subprocess-import] - this module drives Git by design.
import tempfile
from pathlib import Path

from repo_local_tools.agent_tools.errors import AgentToolsError
from repo_local_tools.agent_tools.manifest import (
    MANIFEST_PATH,
    ToolRecord,
    load_manifest,
)


class GitError(AgentToolsError):
    """Raised when a managed Git operation cannot proceed safely."""


GIT_EXECUTABLE = shutil.which("git") or "git"


def commit_managed_tool(repository: Path, kind: str, name: str) -> None:
    """Commit the files owned by one managed tool."""
    _run_git(repository, "rev-parse", "--is-inside-work-tree")
    manifest = load_manifest(repository)
    record = _record_for(manifest.records(kind), kind, name)
    allowed_paths = {".gitignore", str(MANIFEST_PATH), *record.files}
    unrelated = _unrelated_changes(repository, allowed_paths)
    if unrelated:
        msg = (
            f"refusing to commit with unrelated changes present: {', '.join(unrelated)}"
        )
        raise GitError(msg)

    action = (
        "Update" if _has_tracked_owned_path(repository, record.files) else "Install"
    )
    _run_git(repository, "add", "-f", "--", *sorted(allowed_paths))
    staged = subprocess.run(  # ruff: ignore[subprocess-without-shell-equals-true] - fixed Git argv, no shell.
        [GIT_EXECUTABLE, "diff", "--cached", "--quiet"],
        cwd=repository,
        check=False,
    )
    if staged.returncode == 0:
        msg = f"no managed changes to commit for {singularize_kind(kind)} {name}"
        raise GitError(msg)

    subject = _commit_subject(kind, name, action)
    body = _commit_body(kind, name, action)
    with tempfile.TemporaryDirectory() as message_directory:
        message_path = Path(message_directory) / "COMMIT_MSG.md"
        message_path.write_text(f"{subject}\n\n{body}\n")
        _run_git(repository, "commit", "-F", str(message_path))


def _record_for(records: dict[str, ToolRecord], kind: str, name: str) -> ToolRecord:
    """Return the named managed record, or raise GitError if it is unknown."""
    record = records.get(name)
    if record is not None:
        return record
    msg = f"unknown managed {singularize_kind(kind)}: {name}"
    raise GitError(msg)


def _unrelated_changes(repository: Path, allowed_paths: set[str]) -> list[str]:
    """List changed repository paths that fall outside the allowed set."""
    result = _run_git(repository, "status", "--porcelain=v1", "--untracked-files=all")
    unrelated: list[str] = []
    for line in result.stdout.splitlines():
        path = _status_path(line)
        if not _is_allowed(path, allowed_paths):
            unrelated.append(path)
    return unrelated


def _status_path(line: str) -> str:
    """Extract the current path from a porcelain status line."""
    path = line[3:]
    if " -> " in path:
        return path.split(" -> ", maxsplit=1)[1]
    return path


def _is_allowed(path: str, allowed_paths: set[str]) -> bool:
    """Return whether path equals, or sits under, an allowed path."""
    for allowed_path in allowed_paths:
        if path == allowed_path or path.startswith(f"{allowed_path}/"):
            return True
    return False


def _has_tracked_owned_path(repository: Path, files: tuple[str, ...]) -> bool:
    """Return whether Git tracks any of the owned files."""
    for path in files:
        result = subprocess.run(  # ruff: ignore[subprocess-without-shell-equals-true] - Git argv; the path is one argument, no shell.
            [GIT_EXECUTABLE, "ls-files", "--error-unmatch", path],
            cwd=repository,
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            return True
    return False


def _commit_subject(kind: str, name: str, action: str) -> str:
    """Build the commit subject for a managed tool change."""
    noun = _tool_noun(kind)
    return f"{action} {noun} {name}"


def _commit_body(kind: str, name: str, action: str) -> str:
    """Build the commit body describing the managed file ownership change."""
    verb = "Update" if action == "Update" else "Add"
    noun = _tool_noun(kind)
    return (
        f"{verb} repo-local agent client files for the {name} {noun} and "
        "record the managed file ownership metadata."
    )


def singularize_kind(kind: str) -> str:
    """Return a stable singular form for known manifest kinds."""
    mapping = {
        "indices": "index",
        "mcps": "MCP server",
        "metadata": "metadata",
        "skills": "skill",
    }
    return mapping.get(kind, kind.rstrip("s") or kind)


def _tool_noun(kind: str) -> str:
    """Return the singular noun used in commit messages for a kind."""
    return singularize_kind(kind)


def _run_git(repository: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """Run a Git command in repository, raising GitError when it fails."""
    result = subprocess.run(  # ruff: ignore[subprocess-without-shell-equals-true] - Git argv built by callers, no shell.
        [GIT_EXECUTABLE, *args],
        cwd=repository,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        return result
    msg = (
        result.stderr.strip() or result.stdout.strip() or f"git {' '.join(args)} failed"
    )
    raise GitError(msg)
