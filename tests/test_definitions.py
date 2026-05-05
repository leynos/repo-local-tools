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
