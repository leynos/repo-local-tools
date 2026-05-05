"""Client-specific renderers for managed MCP servers and skills."""

from __future__ import annotations

import json
import shutil
import typing as typ
from pathlib import Path

if typ.TYPE_CHECKING:
    from repo_local_tools.agent_tools.definitions import McpDefinition

MCP_CONFIG_PATHS = (
    Path(".mcp.json"),
    Path(".codex/mcp.json"),
    Path(".factory-droid/mcp.json"),
    Path(".cursor/mcp.json"),
)

SKILL_ROOTS = (
    Path(".claude/skills"),
    Path(".codex/skills"),
    Path(".factory-droid/skills"),
    Path(".cursor/skills"),
)


def write_mcp_client_configs(repository: Path, definition: McpDefinition) -> list[Path]:
    """Render one MCP server into each supported repo-local client config."""
    written_paths: list[Path] = []
    for relative_path in MCP_CONFIG_PATHS:
        target = repository / relative_path
        config = _read_json_object(target)
        servers_value = config.get("mcpServers")
        servers: dict[str, object] = (
            typ.cast("dict[str, object]", servers_value)
            if isinstance(servers_value, dict)
            else {}
        )
        config["mcpServers"] = servers
        server: dict[str, object] = {"command": definition.command}
        if definition.args:
            server["args"] = list(definition.args)
        if definition.env:
            server["env"] = definition.env
        servers[definition.name] = server
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(f"{json.dumps(config, indent=2, sort_keys=True)}\n")
        written_paths.append(relative_path)
    return written_paths


def copy_skill_to_clients(repository: Path, name: str, source: Path) -> list[Path]:
    """Copy one skill directory into each supported repo-local client location."""
    written_paths: list[Path] = []
    for root in SKILL_ROOTS:
        relative_path = root / name
        target = repository / relative_path
        if target.exists():
            shutil.rmtree(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source, target)
        written_paths.append(relative_path)
    return written_paths


def _read_json_object(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    parsed = json.loads(path.read_text())
    if isinstance(parsed, dict):
        return parsed
    return {}
