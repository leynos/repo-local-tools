"""Install and update services for managed agent tools."""

from __future__ import annotations

import dataclasses
import tempfile
from pathlib import Path

from repo_local_tools.agent_tools.archives import extract_skill_archive
from repo_local_tools.agent_tools.clients import (
    MCP_CONFIG_PATHS,
    SKILL_ROOTS,
    copy_skill_to_clients,
    write_mcp_client_configs,
)
from repo_local_tools.agent_tools.definitions import load_mcp_definition
from repo_local_tools.agent_tools.errors import AgentToolsError
from repo_local_tools.agent_tools.gitignore import ensure_ignored
from repo_local_tools.agent_tools.manifest import (
    ToolRecord,
    load_manifest,
    save_manifest,
)
from repo_local_tools.agent_tools.paths import data_root


class InstallError(AgentToolsError):
    """Raised when an install or update cannot be completed."""


@dataclasses.dataclass(frozen=True)
class InstallResult:
    """Summary of a managed install or update."""

    name: str
    files: tuple[str, ...]


def install_mcp(
    name: str, repository: Path, xdg_data_home: Path | None
) -> InstallResult:
    """Install one MCP server into the repository."""
    definition = load_mcp_definition(name, xdg_data_home)
    files = tuple(
        str(path) for path in write_mcp_client_configs(repository, definition)
    )
    ignore_patterns = [str(path) for path in MCP_CONFIG_PATHS]
    ensure_ignored(repository, ignore_patterns)
    manifest = load_manifest(repository)
    manifest.mcps[name] = ToolRecord(
        source=str(definition.source_path),
        files=files,
        ignore_patterns=tuple(ignore_patterns),
    )
    save_manifest(repository, manifest)
    return InstallResult(name=name, files=files)


def update_mcps(
    name: str | None,
    repository: Path,
    xdg_data_home: Path | None,
) -> list[InstallResult]:
    """Update one or all installed MCP servers."""
    manifest = load_manifest(repository)
    if name is not None and name not in manifest.mcps:
        msg = f"unknown managed MCP server: {name}"
        raise InstallError(msg)
    names = (name,) if name is not None else tuple(manifest.mcps)
    return [install_mcp(item_name, repository, xdg_data_home) for item_name in names]


def install_skill(
    source: str, repository: Path, xdg_data_home: Path | None
) -> InstallResult:
    """Install one skill from a registry name or absolute `.skill` archive path."""
    if source.endswith(".skill"):
        return _install_skill_archive(_absolute_skill_archive(source), repository)
    skill_source = data_root(xdg_data_home) / "skills" / source
    return _install_skill_directory(source, skill_source, repository, str(skill_source))


def update_skills(
    name: str | None,
    repository: Path,
    xdg_data_home: Path | None,
) -> list[InstallResult]:
    """Update one or all installed skills."""
    manifest = load_manifest(repository)
    names = (name,) if name is not None else tuple(manifest.skills)
    results: list[InstallResult] = []
    for item_name in names:
        record = manifest.skills.get(item_name)
        if record is None:
            msg = f"unknown managed skill: {item_name}"
            raise InstallError(msg)
        if record.source.endswith(".skill"):
            results.append(
                _install_skill_archive(
                    _absolute_skill_archive(record.source), repository, item_name
                )
            )
        else:
            results.append(
                _install_skill_directory(
                    item_name, Path(record.source), repository, record.source
                )
            )
    return results


def _install_skill_archive(
    archive_path: Path,
    repository: Path,
    managed_name: str | None = None,
) -> InstallResult:
    with tempfile.TemporaryDirectory() as temporary_directory:
        extracted = extract_skill_archive(
            archive_path, Path(temporary_directory) / "skill"
        )
        name = managed_name or extracted.name
        return _install_skill_directory(name, extracted, repository, str(archive_path))


def _absolute_skill_archive(source: str) -> Path:
    archive_path = Path(source)
    if archive_path.is_absolute():
        return archive_path
    msg = "Anthropic .skill archives must be absolute paths"
    raise InstallError(msg)


def _install_skill_directory(
    name: str,
    source: Path,
    repository: Path,
    recorded_source: str,
) -> InstallResult:
    if not source.exists() or not source.is_dir():
        msg = f"unknown skill source: {source}"
        raise InstallError(msg)
    files = tuple(str(path) for path in copy_skill_to_clients(repository, name, source))
    ignore_patterns = [str(root) + "/" for root in SKILL_ROOTS]
    ensure_ignored(repository, ignore_patterns)
    manifest = load_manifest(repository)
    manifest.skills[name] = ToolRecord(
        source=recorded_source,
        files=files,
        ignore_patterns=tuple(ignore_patterns),
    )
    save_manifest(repository, manifest)
    return InstallResult(name=name, files=files)
