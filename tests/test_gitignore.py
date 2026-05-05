from __future__ import annotations

from pathlib import Path

from repo_local_tools.agent_tools.gitignore import ensure_ignored


def test_ensure_ignored_adds_missing_entries_once(tmp_path: Path) -> None:
    gitignore = tmp_path / ".gitignore"

    ensure_ignored(tmp_path, [".mcp.json", ".codex/mcp.json"])
    ensure_ignored(tmp_path, [".mcp.json", ".codex/mcp.json"])

    assert gitignore.read_text().splitlines() == [
        "# repo-local-tools managed agent tools",
        ".mcp.json",
        ".codex/mcp.json",
    ]
