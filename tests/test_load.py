from __future__ import annotations

import json
import typing as typ
import zipfile
from pathlib import Path

import pytest

from repo_local_tools.agent_tools.load import LoadError, load_path

if typ.TYPE_CHECKING:
    from syrupy.assertion import SnapshotAssertion


def test_load_directory_discovers_all_supported_sources(tmp_path: Path) -> None:
    source = tmp_path / "workspace" / "project-skill"
    xdg_data_home = tmp_path / "xdg"
    source.mkdir(parents=True)
    (source / "SKILL.md").write_text("Root skill.\n")
    (source / "mcp.json").write_text(
        json.dumps(
            {
                "mcpServers": {
                    "echo": {
                        "command": "python",
                        "args": ["-m", "example"],
                        "env": {"MODE": "test"},
                    },
                },
            },
        ),
    )
    with zipfile.ZipFile(source / "archived.skill", "w") as archive:
        archive.writestr("archived/SKILL.md", "Archived skill.\n")
    nested = source / "skills" / "nested"
    nested.mkdir(parents=True)
    (nested / "SKILL.md").write_text("Nested skill.\n")

    results = load_path(None, source, xdg_data_home)

    assert sorted(result.name for result in results) == [
        "archived",
        "echo",
        "nested",
        "project-skill",
    ]
    assert (
        xdg_data_home / "repo-local-tools" / "skills" / "project-skill" / "SKILL.md"
    ).read_text() == "Root skill.\n"
    assert (
        xdg_data_home / "repo-local-tools" / "skills" / "nested" / "SKILL.md"
    ).read_text() == "Nested skill.\n"
    assert (
        xdg_data_home / "repo-local-tools" / "skills" / "archived" / "SKILL.md"
    ).read_text() == "Archived skill.\n"

    mcp_definition = (
        xdg_data_home / "repo-local-tools" / "mcp-servers" / "echo.toml"
    ).read_text()
    assert 'name = "echo"' in mcp_definition
    assert 'command = "python"' in mcp_definition
    assert 'args = ["-m", "example"]' in mcp_definition
    assert 'MODE = "test"' in mcp_definition


def test_load_skill_md_uses_frontmatter_name(tmp_path: Path) -> None:
    source = tmp_path / "src"
    xdg_data_home = tmp_path / "xdg"
    source.mkdir()
    (source / "SKILL.md").write_text(
        "---\nname: code-reviewer\ndescription: Review code.\n---\n\nUse evidence.\n",
    )

    results = load_path(source / "SKILL.md", tmp_path, xdg_data_home)

    assert [result.name for result in results] == ["code-reviewer"]
    assert (
        (xdg_data_home / "repo-local-tools" / "skills" / "code-reviewer" / "SKILL.md")
        .read_text()
        .startswith("---\nname: code-reviewer\n")
    )


def test_load_skill_md_rejects_ambiguous_directory_names(tmp_path: Path) -> None:
    source = tmp_path / "skill"
    source.mkdir()
    (source / "SKILL.md").write_text("No frontmatter.\n")

    with pytest.raises(LoadError, match="invalid skill name"):
        load_path(source / "SKILL.md", tmp_path, tmp_path / "xdg")


def test_load_mcp_json_rejects_non_string_environment(tmp_path: Path) -> None:
    source = tmp_path / "mcp.json"
    source.write_text(
        json.dumps(
            {
                "mcpServers": {
                    "echo": {
                        "command": "python",
                        "env": {"PORT": 9000},
                    },
                },
            },
        ),
    )

    with pytest.raises(LoadError, match="env"):
        load_path(source, tmp_path, tmp_path / "xdg")


def test_load_mcp_json_wraps_json_decode_error(tmp_path: Path) -> None:
    source = tmp_path / "mcp.json"
    source.write_text('{"mcpServers": ')

    with pytest.raises(LoadError, match="must contain valid JSON"):
        load_path(source, tmp_path, tmp_path / "xdg")


def test_load_mcp_json_file_loads_every_server(tmp_path: Path) -> None:
    source = tmp_path / "mcp.json"
    xdg_data_home = tmp_path / "xdg"
    source.write_text(
        json.dumps(
            {
                "mcpServers": {
                    "alpha": {"command": "python"},
                    "bravo": {"command": "node"},
                },
            },
        ),
    )

    results = load_path(source, tmp_path, xdg_data_home)

    assert [result.name for result in results] == ["alpha", "bravo"]
    assert (xdg_data_home / "repo-local-tools" / "mcp-servers" / "alpha.toml").exists()
    assert (xdg_data_home / "repo-local-tools" / "mcp-servers" / "bravo.toml").exists()


def test_load_mcp_json_snapshot(
    tmp_path: Path,
    snapshot: SnapshotAssertion,
) -> None:
    source = tmp_path / "mcpServers.json"
    xdg_data_home = tmp_path / "xdg"
    source.write_text(
        json.dumps(
            {
                "mcpServers": {
                    "echo": {
                        "command": "python",
                        "args": ["-m", "example"],
                        "env": {"MODE": "test"},
                    },
                },
            },
        ),
    )

    load_path(source, tmp_path, xdg_data_home)

    definition = xdg_data_home / "repo-local-tools" / "mcp-servers" / "echo.toml"
    assert definition.read_text() == snapshot
