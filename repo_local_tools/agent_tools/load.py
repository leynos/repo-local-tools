"""Load local agent tool sources into the shared registry."""

from __future__ import annotations

import dataclasses
import json
import re
import shutil
import tempfile
import typing as typ
from pathlib import Path

from repo_local_tools.agent_tools.archives import ArchiveError, extract_skill_archive
from repo_local_tools.agent_tools.definitions import McpDefinition
from repo_local_tools.agent_tools.errors import AgentToolsError
from repo_local_tools.agent_tools.paths import data_root

if typ.TYPE_CHECKING:
    import collections.abc as cabc

MCP_JSON_FILENAMES = frozenset({"mcp.json", "mcpServers.json"})
INVALID_FALLBACK_SKILL_NAMES = frozenset({"skill", "src"})
SKILL_NAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]*$")
MCP_NAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


class LoadError(AgentToolsError):
    """Raised when local tool sources cannot be loaded."""


@dataclasses.dataclass(frozen=True, slots=True)
class LoadResult:
    """Summary of one loaded shared registry item."""

    kind: str
    name: str
    path: Path


@dataclasses.dataclass(frozen=True, slots=True)
class _LoadCandidate:
    result: LoadResult
    write: cabc.Callable[[], LoadResult]


def load_path(
    source: Path | None,
    cwd: Path,
    xdg_data_home: Path | None,
) -> list[LoadResult]:
    """Load local skill and MCP sources into the shared XDG registry."""
    target = cwd if source is None else _resolve_source(source, cwd)
    if target.is_file():
        return _load_file(target, xdg_data_home)
    if target.is_dir():
        return _load_directory(target, xdg_data_home)
    msg = f"load source does not exist: {target}"
    raise LoadError(msg)


def _resolve_source(source: Path, cwd: Path) -> Path:
    if source.is_absolute():
        return source
    return cwd / source


def _load_file(source: Path, xdg_data_home: Path | None) -> list[LoadResult]:
    if source.name == "SKILL.md":
        return [_load_skill_directory(source.parent, xdg_data_home)]
    if source.suffix == ".skill":
        return [_load_skill_archive(source, xdg_data_home)]
    if source.name in MCP_JSON_FILENAMES:
        return _load_mcp_json(source, xdg_data_home)
    msg = f"unsupported load source: {source}"
    raise LoadError(msg)


def _load_directory(source: Path, xdg_data_home: Path | None) -> list[LoadResult]:
    loaders: list[cabc.Callable[[], list[_LoadCandidate]]] = []
    if (source / "SKILL.md").exists():
        loaders.append(lambda: [_skill_directory_candidate(source, xdg_data_home)])
    for mcp_filename in sorted(MCP_JSON_FILENAMES):
        mcp_source = source / mcp_filename
        if mcp_source.exists():
            loaders.append(
                lambda mcp_source=mcp_source: _mcp_json_candidates(
                    mcp_source, xdg_data_home
                )
            )
    loaders.extend(
        (
            lambda archive_path=archive_path: [
                _skill_archive_candidate(archive_path, xdg_data_home)
            ]
        )
        for archive_path in sorted(source.glob("*.skill"))
    )
    for skill_root_name in ("skill", "skills"):
        skill_root = source / skill_root_name
        if skill_root.is_dir():
            loaders.extend(
                lambda skill_directory=skill_directory: [
                    _skill_directory_candidate(skill_directory, xdg_data_home)
                ]
                for skill_directory in sorted(skill_root.iterdir())
                if skill_directory.is_dir()
            )

    candidates = [candidate for loader in loaders for candidate in loader()]
    if candidates:
        _reject_duplicate_results(candidate.result for candidate in candidates)
        return [candidate.write() for candidate in candidates]
    msg = f"no supported tool sources found in {source}"
    raise LoadError(msg)


def _reject_duplicate_results(results: typ.Iterable[LoadResult]) -> None:
    seen: set[tuple[str, str]] = set()
    duplicates: set[tuple[str, str]] = set()
    for result in results:
        key = (result.kind, result.name)
        if key in seen:
            duplicates.add(key)
        else:
            seen.add(key)
    if duplicates:
        duplicate_names = ", ".join(
            f"{kind} {name!r}" for kind, name in sorted(duplicates)
        )
        msg = f"duplicate load results: {duplicate_names}"
        raise LoadError(msg)


def _skill_archive_candidate(
    archive_path: Path,
    xdg_data_home: Path | None,
) -> _LoadCandidate:
    with tempfile.TemporaryDirectory() as temporary_directory:
        extracted = _extract_archive_for_load(
            archive_path.resolve(), Path(temporary_directory) / "skill"
        )
        name = _skill_name(extracted / "SKILL.md", extracted.name)
    return _LoadCandidate(
        result=_skill_result(name, xdg_data_home),
        write=lambda: _load_skill_archive(archive_path, xdg_data_home),
    )


def _load_skill_archive(archive_path: Path, xdg_data_home: Path | None) -> LoadResult:
    with tempfile.TemporaryDirectory() as temporary_directory:
        extracted = _extract_archive_for_load(
            archive_path.resolve(), Path(temporary_directory) / "skill"
        )
        name = _skill_name(extracted / "SKILL.md", extracted.name)
        return _copy_skill_to_registry(name, extracted, xdg_data_home)


def _extract_archive_for_load(archive_path: Path, extract_root: Path) -> Path:
    try:
        return extract_skill_archive(archive_path, extract_root)
    except ArchiveError as error:
        msg = f"failed to load skill archive: {archive_path}"
        raise LoadError(msg) from error


def _skill_directory_candidate(
    source: Path,
    xdg_data_home: Path | None,
) -> _LoadCandidate:
    skill_file = source / "SKILL.md"
    if not skill_file.exists():
        msg = f"skill source must contain SKILL.md: {source}"
        raise LoadError(msg)
    _reject_skill_symlinks(source)
    name = _skill_name(skill_file, source.name)
    return _LoadCandidate(
        result=_skill_result(name, xdg_data_home),
        write=lambda: _load_skill_directory(source, xdg_data_home),
    )


def _load_skill_directory(source: Path, xdg_data_home: Path | None) -> LoadResult:
    skill_file = source / "SKILL.md"
    if not skill_file.exists():
        msg = f"skill source must contain SKILL.md: {source}"
        raise LoadError(msg)
    name = _skill_name(skill_file, source.name)
    return _copy_skill_to_registry(name, source, xdg_data_home)


def _skill_result(name: str, xdg_data_home: Path | None) -> LoadResult:
    return LoadResult(
        kind="skill",
        name=name,
        path=data_root(xdg_data_home) / "skills" / name,
    )


def _skill_name(skill_file: Path, fallback: str) -> str:
    name = _frontmatter_name(skill_file) or fallback
    if name in INVALID_FALLBACK_SKILL_NAMES or not SKILL_NAME_PATTERN.fullmatch(name):
        msg = f"invalid skill name: {name}"
        raise LoadError(msg)
    return name


def _frontmatter_name(skill_file: Path) -> str | None:
    lines = skill_file.read_text().splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    for line in lines[1:]:
        stripped = line.strip()
        if stripped == "---":
            return None
        key, separator, value = stripped.partition(":")
        if separator and key.strip() == "name":
            return value.strip().strip("\"'")
    return None


def _copy_skill_to_registry(
    name: str,
    source: Path,
    xdg_data_home: Path | None,
) -> LoadResult:
    _reject_skill_symlinks(source)
    destination = data_root(xdg_data_home) / "skills" / name
    if destination.exists():
        shutil.rmtree(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, destination)
    return LoadResult(kind="skill", name=name, path=destination)


def _reject_skill_symlinks(source: Path) -> None:
    if source.is_symlink():
        msg = f"skill source must not be a symlink: {source}"
        raise LoadError(msg)
    for path in source.rglob("*"):
        if path.is_symlink():
            msg = f"skill source must not contain symlinks: {path}"
            raise LoadError(msg)


def _load_mcp_json(source: Path, xdg_data_home: Path | None) -> list[LoadResult]:
    return [
        candidate.write() for candidate in _mcp_json_candidates(source, xdg_data_home)
    ]


def _mcp_json_candidates(
    source: Path,
    xdg_data_home: Path | None,
) -> list[_LoadCandidate]:
    try:
        parsed = json.loads(source.read_text())
    except json.JSONDecodeError as error:
        msg = f"{source} must contain valid JSON: {error.msg}"
        raise LoadError(msg) from error
    if not isinstance(parsed, dict):
        msg = f"{source} must contain a JSON object"
        raise LoadError(msg)
    servers_value = parsed.get("mcpServers")
    if not isinstance(servers_value, dict) or not servers_value:
        msg = f"{source} must define a non-empty mcpServers object"
        raise LoadError(msg)

    candidates: list[_LoadCandidate] = []
    for name, value in sorted(servers_value.items()):
        definition = _mcp_definition(source, name, value)
        candidates.append(
            _LoadCandidate(
                result=_mcp_result(definition.name, xdg_data_home),
                write=lambda definition=definition: _write_mcp_definition(
                    definition, xdg_data_home
                ),
            )
        )
    return candidates


def _mcp_result(name: str, xdg_data_home: Path | None) -> LoadResult:
    return LoadResult(
        kind="mcp",
        name=name,
        path=data_root(xdg_data_home) / "mcp-servers" / f"{name}.toml",
    )


def _mcp_definition(source: Path, name: object, value: object) -> McpDefinition:
    safe_name = _safe_mcp_name(source, name)
    if not isinstance(value, dict):
        msg = f"{source} MCP server {safe_name!r} must be an object"
        raise LoadError(msg)
    parsed = typ.cast("dict[object, object]", value)
    command = _required_string(parsed, "command", source, safe_name)
    args = _optional_string_tuple(parsed, "args", source, safe_name)
    env = _optional_string_mapping(parsed, "env", source, safe_name)
    return McpDefinition(
        name=safe_name,
        command=command,
        args=args,
        env=env,
        source_path=source,
    )


def _safe_mcp_name(source: Path, name: object) -> str:
    if not isinstance(name, str) or not name:
        msg = f"{source} contains an MCP server with an invalid name"
        raise LoadError(msg)
    unsafe_checks = (
        Path(name).is_absolute(),
        "/" in name,
        "\\" in name,
        ".." in name,
        MCP_NAME_PATTERN.fullmatch(name) is None,
    )
    if any(unsafe_checks):
        msg = f"{source} contains unsafe MCP server name: {name!r}"
        raise LoadError(msg)
    return name


def _required_string(
    parsed: dict[object, object],
    key: str,
    source: Path,
    name: str,
) -> str:
    value = parsed.get(key)
    if isinstance(value, str) and value:
        return value
    msg = f"{source} MCP server {name!r} must define non-empty string field {key!r}"
    raise LoadError(msg)


def _optional_string_tuple(
    parsed: dict[object, object],
    key: str,
    source: Path,
    name: str,
) -> tuple[str, ...]:
    value = parsed.get(key, [])
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        msg = f"{source} MCP server {name!r} field {key!r} must be a list of strings"
        raise LoadError(msg)
    return tuple(typ.cast("list[str]", value))


def _optional_string_mapping(
    parsed: dict[object, object],
    key: str,
    source: Path,
    name: str,
) -> dict[str, str]:
    value = parsed.get(key, {})
    if not isinstance(value, dict):
        msg = f"{source} MCP server {name!r} field {key!r} must be an object"
        raise LoadError(msg)
    env: dict[str, str] = {}
    for item_key, item_value in value.items():
        if not isinstance(item_key, str) or not isinstance(item_value, str):
            msg = (
                f"{source} MCP server {name!r} field {key!r} must be an object "
                "of string values"
            )
            raise LoadError(msg)
        env[item_key] = item_value
    return env


def _write_mcp_definition(
    definition: McpDefinition,
    xdg_data_home: Path | None,
) -> LoadResult:
    name = definition.name
    destination = data_root(xdg_data_home) / "mcp-servers" / f"{name}.toml"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(_mcp_definition_toml(definition))
    return LoadResult(kind="mcp", name=name, path=destination)


def _mcp_definition_toml(definition: McpDefinition) -> str:
    lines = [
        f"name = {_toml_string(definition.name)}",
        f"command = {_toml_string(definition.command)}",
    ]
    if definition.args:
        args = ", ".join(_toml_string(item) for item in definition.args)
        lines.append(f"args = [{args}]")
    if definition.env:
        lines.extend(("", "[env]"))
        lines.extend(
            f"{_toml_string(key)} = {_toml_string(value)}"
            for key, value in sorted(definition.env.items())
        )
    return "\n".join(lines) + "\n"


def _toml_string(value: str) -> str:
    return json.dumps(value)
