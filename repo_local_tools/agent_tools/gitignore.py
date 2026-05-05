"""Idempotent `.gitignore` updates for managed agent tool files."""

from __future__ import annotations

import typing as typ

if typ.TYPE_CHECKING:
    from pathlib import Path

HEADER = "# repo-local-tools managed agent tools"


def ensure_ignored(repository: Path, patterns: list[str]) -> list[str]:
    """Ensure `.gitignore` contains the managed tool ignore patterns."""
    gitignore = repository / ".gitignore"
    lines = gitignore.read_text().splitlines() if gitignore.exists() else []
    changed: list[str] = []
    if patterns and HEADER not in lines:
        if lines and lines[-1] != "":
            lines.append("")
        lines.append(HEADER)
    for pattern in patterns:
        if pattern not in lines:
            lines.append(pattern)
            changed.append(pattern)
    if changed:
        content = "\n".join(lines)
        gitignore.write_text(f"{content}\n")
    return changed
