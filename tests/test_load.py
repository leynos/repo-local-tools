"""Tests for local tool loading via `load_path` and `LoadError`.

The tests cover loading skill directories, `SKILL.md` files, `.skill` archives,
MCP JSON files, and error cases. Pytest discovers functions prefixed with
`test_`; example: `results = load_path(source, tmp_path, xdg_data_home)`.
"""

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
                        "env": {"APP.MODE": "test"},
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

    actual_names = sorted(result.name for result in results)
    assert actual_names == [
        "archived",
        "echo",
        "nested",
        "project-skill",
    ], (
        "unexpected loaded result names: expected archived, echo, nested, "
        f"project-skill; found {actual_names!r}"
    )
    project_skill_path = (
        xdg_data_home / "repo-local-tools" / "skills" / "project-skill" / "SKILL.md"
    )
    nested_skill_path = (
        xdg_data_home / "repo-local-tools" / "skills" / "nested" / "SKILL.md"
    )
    archived_skill_path = (
        xdg_data_home / "repo-local-tools" / "skills" / "archived" / "SKILL.md"
    )
    assert project_skill_path.read_text() == "Root skill.\n", (
        f"unexpected generated SKILL.md content at {project_skill_path}: "
        "expected 'Root skill.\\n'"
    )
    assert nested_skill_path.read_text() == "Nested skill.\n", (
        f"unexpected generated SKILL.md content at {nested_skill_path}: "
        "expected 'Nested skill.\\n'"
    )
    assert archived_skill_path.read_text() == "Archived skill.\n", (
        f"unexpected generated SKILL.md content at {archived_skill_path}: "
        "expected 'Archived skill.\\n'"
    )

    mcp_definition = (
        xdg_data_home / "repo-local-tools" / "mcp-servers" / "echo.toml"
    ).read_text()
    assert 'name = "echo"' in mcp_definition, (
        f"expected MCP TOML to contain echo name; content: {mcp_definition!r}"
    )
    assert 'command = "python"' in mcp_definition, (
        f"expected MCP TOML to contain python command; content: {mcp_definition!r}"
    )
    assert 'args = ["-m", "example"]' in mcp_definition, (
        f"expected MCP TOML to contain example args; content: {mcp_definition!r}"
    )
    assert '"APP.MODE" = "test"' in mcp_definition, (
        f"expected MCP TOML to contain APP.MODE env; content: {mcp_definition!r}"
    )


def test_load_directory_rejects_duplicate_skill_results(tmp_path: Path) -> None:
    source = tmp_path / "workspace" / "reviewer"
    xdg_data_home = tmp_path / "xdg"
    source.mkdir(parents=True)
    (source / "SKILL.md").write_text("Root skill.\n")
    nested = source / "skills" / "reviewer"
    nested.mkdir(parents=True)
    (nested / "SKILL.md").write_text("Nested skill.\n")

    with pytest.raises(LoadError, match="duplicate load results: skill 'reviewer'"):
        load_path(None, source, xdg_data_home)

    registry_path = xdg_data_home / "repo-local-tools" / "skills" / "reviewer"
    assert not registry_path.exists(), (
        f"expected duplicate load to avoid writing {registry_path}"
    )


def test_load_directory_rejects_duplicate_mcp_results(tmp_path: Path) -> None:
    source = tmp_path / "workspace"
    xdg_data_home = tmp_path / "xdg"
    source.mkdir()
    payload = json.dumps({"mcpServers": {"echo": {"command": "python"}}})
    (source / "mcp.json").write_text(payload)
    (source / "mcpServers.json").write_text(payload)

    with pytest.raises(LoadError, match="duplicate load results: mcp 'echo'"):
        load_path(None, source, xdg_data_home)

    registry_path = xdg_data_home / "repo-local-tools" / "mcp-servers" / "echo.toml"
    assert not registry_path.exists(), (
        f"expected duplicate load to avoid writing {registry_path}"
    )


def test_load_skill_archive_wraps_archive_error(tmp_path: Path) -> None:
    archive = tmp_path / "corrupt.skill"
    archive.write_text("not a zip archive")

    with pytest.raises(LoadError, match="failed to load skill archive") as error:
        load_path(archive, tmp_path, tmp_path / "xdg")

    assert error.value.__cause__ is not None, "expected original archive error cause"


def test_load_skill_directory_rejects_symlink_source(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "SKILL.md").write_text("Skill body.\n")
    symlink = tmp_path / "linked-skill"
    symlink.symlink_to(source, target_is_directory=True)

    with pytest.raises(LoadError, match="skill source must not be a symlink"):
        load_path(symlink, tmp_path, tmp_path / "xdg")


def test_load_skill_directory_rejects_nested_symlink(tmp_path: Path) -> None:
    source = tmp_path / "source"
    outside = tmp_path / "outside.txt"
    source.mkdir()
    (source / "SKILL.md").write_text("Skill body.\n")
    outside.write_text("outside\n")
    (source / "outside-link.txt").symlink_to(outside)

    with pytest.raises(LoadError, match="skill source must not contain symlinks"):
        load_path(source, tmp_path, tmp_path / "xdg")


def test_load_skill_md_rejects_nested_symlink(tmp_path: Path) -> None:
    source = tmp_path / "source"
    outside = tmp_path / "outside.txt"
    source.mkdir()
    (source / "SKILL.md").write_text("Skill body.\n")
    outside.write_text("outside\n")
    (source / "outside-link.txt").symlink_to(outside)

    with pytest.raises(LoadError, match="skill source must not contain symlinks"):
        load_path(source / "SKILL.md", tmp_path, tmp_path / "xdg")


def test_load_directory_rejects_symlink_candidate_before_writes(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    xdg_data_home = tmp_path / "xdg"
    valid = workspace / "skills" / "alpha"
    invalid = workspace / "skills" / "bravo"
    outside = tmp_path / "outside.txt"
    valid.mkdir(parents=True)
    invalid.mkdir()
    outside.write_text("outside\n")
    (valid / "SKILL.md").write_text("Valid skill.\n")
    (invalid / "SKILL.md").write_text("Invalid skill.\n")
    (invalid / "outside-link.txt").symlink_to(outside)

    with pytest.raises(LoadError, match="skill source must not contain symlinks"):
        load_path(None, workspace, xdg_data_home)

    registry = xdg_data_home / "repo-local-tools" / "skills"
    assert not registry.exists(), (
        f"expected failed candidate collection to leave registry unchanged: {registry}"
    )


def test_load_skill_md_uses_frontmatter_name(tmp_path: Path) -> None:
    source = tmp_path / "src"
    xdg_data_home = tmp_path / "xdg"
    source.mkdir()
    (source / "SKILL.md").write_text(
        "---\nname: code-reviewer\ndescription: Review code.\n---\n\nUse evidence.\n",
    )

    results = load_path(source / "SKILL.md", tmp_path, xdg_data_home)

    actual_names = [result.name for result in results]
    assert actual_names == ["code-reviewer"], (
        f"unexpected loaded result names: expected ['code-reviewer'], "
        f"found {actual_names!r}"
    )
    skill_path = (
        xdg_data_home / "repo-local-tools" / "skills" / "code-reviewer" / "SKILL.md"
    )
    skill_content = skill_path.read_text()
    assert skill_content.startswith("---\nname: code-reviewer\n"), (
        f"expected frontmatter name to be preserved in {skill_path}; "
        f"content: {skill_content!r}"
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


@pytest.mark.parametrize(
    "name",
    ["../escape", "/" + "tmp/owned", r"bad\name", "bad/name"],
)
def test_load_mcp_json_rejects_unsafe_server_names(
    tmp_path: Path,
    name: str,
) -> None:
    source = tmp_path / "mcp.json"
    source.write_text(json.dumps({"mcpServers": {name: {"command": "python"}}}))

    with pytest.raises(LoadError, match="unsafe MCP server name"):
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

    actual_names = [result.name for result in results]
    assert actual_names == ["alpha", "bravo"], (
        f"unexpected loaded MCP result names: expected ['alpha', 'bravo'], "
        f"found {actual_names!r}"
    )
    alpha_definition = xdg_data_home / "repo-local-tools" / "mcp-servers" / "alpha.toml"
    bravo_definition = xdg_data_home / "repo-local-tools" / "mcp-servers" / "bravo.toml"
    assert alpha_definition.exists(), (
        f"expected generated MCP TOML for alpha at {alpha_definition}"
    )
    assert bravo_definition.exists(), (
        f"expected generated MCP TOML for bravo at {bravo_definition}"
    )


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
                        "env": {"APP.MODE": "test"},
                    },
                },
            },
        ),
    )

    load_path(source, tmp_path, xdg_data_home)

    definition = xdg_data_home / "repo-local-tools" / "mcp-servers" / "echo.toml"
    actual_definition = definition.read_text()
    assert actual_definition == snapshot, (
        f"snapshot mismatch for generated MCP TOML at {definition}: "
        f"{actual_definition!r}"
    )
