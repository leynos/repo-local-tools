from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest

from conftest import write_mcp_definition
from repo_local_tools.agent_tools.install import (
    InstallError,
    install_mcp,
    install_skill,
    update_mcps,
    update_skills,
)
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
        actual_command = config["mcpServers"]["echo"]["command"]
        assert actual_command == "python", (
            f"unexpected MCP command in {relative_path}: "
            f"expected 'python', found {actual_command!r}; config: {config!r}"
        )

    manifest = load_manifest(repository)
    assert "echo" in manifest.mcps, (
        f"manifest missing 'echo' MCP entry; mcps: {manifest.mcps!r}"
    )


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
        content = (repository / relative_path).read_text()
        assert content == "Use evidence.\n", (
            f"unexpected content in {relative_path}: {content!r}"
        )

    manifest = load_manifest(repository)
    assert "reviewer" in manifest.skills, (
        f"manifest missing 'reviewer' skill; skills: {manifest.skills!r}"
    )


def test_install_skill_rejects_relative_archive_path(tmp_path: Path) -> None:
    repository = tmp_path / "repo"
    repository.mkdir()

    with pytest.raises(InstallError, match="absolute path"):
        install_skill("relative/path/reviewer.skill", repository, tmp_path / "xdg")


def test_install_skill_from_archive_path_updates_manifest_and_clients(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "repo"
    archive_path = tmp_path / "archives" / "reviewer.skill"
    repository.mkdir()
    archive_path.parent.mkdir()
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("reviewer/SKILL.md", "From archive.\n")

    install_skill(str(archive_path), repository, tmp_path / "xdg")

    for relative_path in [
        ".claude/skills/reviewer/SKILL.md",
        ".codex/skills/reviewer/SKILL.md",
        ".factory-droid/skills/reviewer/SKILL.md",
        ".cursor/skills/reviewer/SKILL.md",
    ]:
        assert (repository / relative_path).read_text() == "From archive.\n"

    manifest = load_manifest(repository)
    assert manifest.skills["reviewer"].source == str(archive_path)


def test_update_skill_archive_preserves_managed_name(tmp_path: Path) -> None:
    repository = tmp_path / "repo"
    archive_path = tmp_path / "archives" / "reviewer.skill"
    repository.mkdir()
    archive_path.parent.mkdir()
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("reviewer/SKILL.md", "Initial archive.\n")

    install_skill(str(archive_path), repository, tmp_path / "xdg")
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("renamed-upstream/SKILL.md", "Updated archive.\n")

    results = update_skills("reviewer", repository, tmp_path / "xdg")

    assert [result.name for result in results] == ["reviewer"]
    assert (
        repository / ".claude/skills/reviewer/SKILL.md"
    ).read_text() == "Updated archive.\n"
    assert not (repository / ".claude/skills/renamed-upstream").exists()
    manifest = load_manifest(repository)
    assert set(manifest.skills) == {"reviewer"}


def test_install_skill_unknown_name_raises_install_error(tmp_path: Path) -> None:
    repository = tmp_path / "repo"
    repository.mkdir()

    with pytest.raises(InstallError, match="unknown skill source"):
        install_skill("unknown-skill", repository, tmp_path / "xdg")


def test_update_mcps_requires_named_tool_to_be_installed(tmp_path: Path) -> None:
    repository = tmp_path / "repo"
    xdg_data_home = tmp_path / "xdg"
    repository.mkdir()
    write_mcp_definition(xdg_data_home, "echo")

    with pytest.raises(InstallError, match="unknown managed MCP server"):
        update_mcps("echo", repository, xdg_data_home)


def test_update_mcps_and_skills_return_install_results(tmp_path: Path) -> None:
    repository = tmp_path / "repo"
    xdg_data_home = tmp_path / "xdg"
    repository.mkdir()
    write_mcp_definition(xdg_data_home, "echo")
    write_skill_definition(xdg_data_home, "reviewer")
    install_mcp("echo", repository, xdg_data_home)
    install_skill("reviewer", repository, xdg_data_home)

    mcp_results = update_mcps(None, repository, xdg_data_home)
    skill_results = update_skills(None, repository, xdg_data_home)

    assert {result.name for result in mcp_results} == {"echo"}
    assert {result.name for result in skill_results} == {"reviewer"}


def write_skill_definition(xdg_data_home: Path, name: str) -> None:
    skill = xdg_data_home / "repo-local-tools" / "skills" / name
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("Use evidence.\n")
