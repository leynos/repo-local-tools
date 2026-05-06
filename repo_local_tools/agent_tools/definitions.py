"""Shared source definition loading and validation."""

from __future__ import annotations

import dataclasses
import tomllib
import typing as typ

from repo_local_tools.agent_tools.errors import AgentToolsError
from repo_local_tools.agent_tools.paths import data_root

if typ.TYPE_CHECKING:
    from pathlib import Path


class DefinitionError(AgentToolsError):
    """Raised when a shared tool definition is invalid."""


@dataclasses.dataclass(frozen=True, slots=True)
class McpDefinition:
    """A shared MCP server definition."""

    name: str
    command: str
    args: tuple[str, ...]
    env: dict[str, str]
    source_path: Path


def load_mcp_definition(name: str, xdg_data_home: Path | None) -> McpDefinition:
    """Load one MCP server definition from the shared registry."""
    definition_path = data_root(xdg_data_home) / "mcp-servers" / f"{name}.toml"
    if not definition_path.exists():
        msg = f"unknown MCP server definition: {name}"
        raise DefinitionError(msg)

    parsed = tomllib.loads(definition_path.read_text())
    definition_name = _required_string(parsed, "name", definition_path)
    if definition_name != name:
        msg = f"MCP definition name {definition_name!r} does not match {name!r}"
        raise DefinitionError(msg)

    command = _required_string(parsed, "command", definition_path)
    args = _optional_string_tuple(parsed, "args", definition_path)
    env = _optional_string_mapping(parsed, "env", definition_path)
    return McpDefinition(
        name=definition_name,
        command=command,
        args=args,
        env=env,
        source_path=definition_path,
    )


def _required_string(parsed: dict[str, object], key: str, source: Path) -> str:
    value = parsed.get(key)
    if isinstance(value, str) and value:
        return value
    msg = f"{source} must define non-empty string field {key!r}"
    raise DefinitionError(msg)


def _optional_string_tuple(
    parsed: dict[str, object],
    key: str,
    source: Path,
) -> tuple[str, ...]:
    value = parsed.get(key, [])
    if not isinstance(value, list):
        msg = f"{source} field {key!r} must be a list of strings"
        raise DefinitionError(msg)
    items: list[str] = []
    for item in value:
        if not isinstance(item, str):
            msg = f"{source} field {key!r} must be a list of strings"
            raise DefinitionError(msg)
        items.append(item)
    return tuple(items)


def _optional_string_mapping(
    parsed: dict[str, object],
    key: str,
    source: Path,
) -> dict[str, str]:
    value = parsed.get(key, {})
    if not isinstance(value, dict):
        msg = f"{source} field {key!r} must be a table of strings"
        raise DefinitionError(msg)
    env: dict[str, str] = {}
    for item_key, item_value in value.items():
        if not isinstance(item_key, str) or not isinstance(item_value, str):
            msg = f"{source} field {key!r} must be a table of strings"
            raise DefinitionError(msg)
        env[item_key] = item_value
    return env
