from __future__ import annotations

from pathlib import Path

import pytest

from repo_local_tools.agent_tools.definitions import (
    DefinitionError,
    load_mcp_definition,
)
from repo_local_tools.agent_tools.paths import data_root


def test_data_root_uses_xdg_data_home(tmp_path: Path) -> None:
    assert data_root(tmp_path) == tmp_path / "repo-local-tools"


def test_data_root_uses_env_when_xdg_data_home_is_none(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))

    assert data_root(None) == tmp_path / "repo-local-tools"


def test_data_root_falls_back_to_home_when_no_xdg(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("XDG_DATA_HOME", raising=False)

    assert data_root(None) == Path.home() / ".local" / "share" / "repo-local-tools"


def test_load_mcp_definition_reads_toml(tmp_path: Path) -> None:
    registry = tmp_path / "repo-local-tools" / "mcp-servers"
    registry.mkdir(parents=True)
    (registry / "echo.toml").write_text(
        'name = "echo"\n'
        'command = "python"\n'
        'args = ["-m", "example"]\n'
        "[env]\n"
        'MODE = "test"\n',
    )

    definition = load_mcp_definition("echo", tmp_path)

    assert definition.name == "echo"
    assert definition.command == "python"
    assert definition.args == ("-m", "example")
    assert definition.env == {"MODE": "test"}


def test_load_mcp_definition_rejects_name_mismatch(tmp_path: Path) -> None:
    registry = tmp_path / "repo-local-tools" / "mcp-servers"
    registry.mkdir(parents=True)
    (registry / "echo.toml").write_text('name = "other"\ncommand = "python"\n')

    with pytest.raises(DefinitionError, match="does not match"):
        load_mcp_definition("echo", tmp_path)


def test_load_mcp_definition_unknown_definition(tmp_path: Path) -> None:
    registry = tmp_path / "repo-local-tools" / "mcp-servers"
    registry.mkdir(parents=True)

    with pytest.raises(DefinitionError, match="unknown MCP server definition"):
        load_mcp_definition("missing", tmp_path)


def test_load_mcp_definition_invalid_args_type(tmp_path: Path) -> None:
    registry = tmp_path / "repo-local-tools" / "mcp-servers"
    registry.mkdir(parents=True)
    (registry / "echo.toml").write_text(
        'name = "echo"\ncommand = "python"\nargs = "not-a-list"\n',
    )

    with pytest.raises(DefinitionError, match="args"):
        load_mcp_definition("echo", tmp_path)


def test_load_mcp_definition_invalid_env_type(tmp_path: Path) -> None:
    registry = tmp_path / "repo-local-tools" / "mcp-servers"
    registry.mkdir(parents=True)
    (registry / "echo.toml").write_text(
        'name = "echo"\ncommand = "python"\nenv = "not-a-table"\n',
    )

    with pytest.raises(DefinitionError, match="env"):
        load_mcp_definition("echo", tmp_path)


def test_load_mcp_definition_missing_command(tmp_path: Path) -> None:
    registry = tmp_path / "repo-local-tools" / "mcp-servers"
    registry.mkdir(parents=True)
    (registry / "echo.toml").write_text('name = "echo"\n')

    with pytest.raises(DefinitionError, match="command"):
        load_mcp_definition("echo", tmp_path)


def test_load_mcp_definition_empty_name(tmp_path: Path) -> None:
    registry = tmp_path / "repo-local-tools" / "mcp-servers"
    registry.mkdir(parents=True)
    (registry / "echo.toml").write_text(
        'name = ""\ncommand = "python"\n',
    )

    with pytest.raises(DefinitionError, match="name"):
        load_mcp_definition("echo", tmp_path)
