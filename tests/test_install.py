from __future__ import annotations

import json
from pathlib import Path

from repo_local_tools.agent_tools.install import install_mcp, install_skill
from repo_local_tools.agent_tools.manifest import load_manifest


def test_install_mcp_writes_supported_client_configs(tmp_path: Path) -> None:
    repository = tmp_path / "repo"
    xdg_data_home = tmp_path / "xdg"
    repository.mkdir()
    write_mcp_definition(xdg_data_home, "echo")

    install_mcp("echo", repository, xdg_data_home)

    for relative_path in [
        ".mcp.json",
        ".codex/mcp.json",
        ".factory-droid/mcp.json",
        ".cursor/mcp.json",
    ]:
        config = json.loads((repository / relative_path).read_text())
        assert config["mcpServers"]["echo"]["command"] == "python"

    manifest = load_manifest(repository)
    assert "echo" in manifest.mcps


def test_install_skill_copies_skill_to_supported_clients(tmp_path: Path) -> None:
    repository = tmp_path / "repo"
    xdg_data_home = tmp_path / "xdg"
    repository.mkdir()
    skill = xdg_data_home / "repo-local-tools" / "skills" / "reviewer"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("Use evidence.\n")

    install_skill("reviewer", repository, xdg_data_home)

    for relative_path in [
        ".claude/skills/reviewer/SKILL.md",
        ".codex/skills/reviewer/SKILL.md",
        ".factory-droid/skills/reviewer/SKILL.md",
        ".cursor/skills/reviewer/SKILL.md",
    ]:
        assert (repository / relative_path).read_text() == "Use evidence.\n"

    manifest = load_manifest(repository)
    assert "reviewer" in manifest.skills


def write_mcp_definition(xdg_data_home: Path, name: str) -> None:
    registry = xdg_data_home / "repo-local-tools" / "mcp-servers"
    registry.mkdir(parents=True)
    (registry / f"{name}.toml").write_text(
        f'name = "{name}"\ncommand = "python"\nargs = ["-m", "example"]\n',
    )
