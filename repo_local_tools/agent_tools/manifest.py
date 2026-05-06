"""Repo-local manifest read and write helpers."""

from __future__ import annotations

import dataclasses
import json
import typing as typ
from pathlib import Path

from repo_local_tools.agent_tools.errors import AgentToolsError

MANIFEST_PATH = Path(".repo-local-tools/managed-tools.json")


class ManifestError(AgentToolsError):
    """Raised when the managed tool manifest is invalid."""


@dataclasses.dataclass(frozen=True, slots=True)
class ToolRecord:
    """Manifest metadata for one managed tool."""

    source: str
    files: tuple[str, ...]
    ignore_patterns: tuple[str, ...]


@dataclasses.dataclass(slots=True)
class Manifest:
    """Repo-local managed tool manifest."""

    mcps: dict[str, ToolRecord]
    skills: dict[str, ToolRecord]

    def records(self, kind: str) -> dict[str, ToolRecord]:
        """Return records for a manifest kind."""
        if kind == "mcps":
            return self.mcps
        elif kind == "skills":  # noqa: RET505
            return self.skills
        msg = f"unknown manifest kind: {kind}"
        raise ValueError(msg)


def load_manifest(repository: Path) -> Manifest:
    """Load the repo-local managed tool manifest."""
    manifest_path = repository / MANIFEST_PATH
    if not manifest_path.exists():
        return Manifest(mcps={}, skills={})
    try:
        parsed = json.loads(manifest_path.read_text())
    except json.JSONDecodeError as exc:
        msg = f"Invalid manifest JSON in {manifest_path}: {exc}"
        raise ManifestError(msg) from exc
    if not isinstance(parsed, dict):
        msg = f"Invalid manifest in {manifest_path}: expected top-level object"
        raise ManifestError(msg)
    mcps = _manifest_section(parsed, "mcps", manifest_path)
    skills = _manifest_section(parsed, "skills", manifest_path)
    return Manifest(
        mcps=_load_records(mcps),
        skills=_load_records(skills),
    )


def save_manifest(repository: Path, manifest: Manifest) -> None:
    """Write the repo-local managed tool manifest."""
    manifest_path = repository / MANIFEST_PATH
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    payload = f"{json.dumps(_dump_manifest(manifest), indent=2, sort_keys=True)}\n"
    temporary_path = manifest_path.with_name(f"{manifest_path.name}.tmp")
    temporary_path.write_text(payload)
    temporary_path.replace(manifest_path)


def _manifest_section(
    parsed: dict[object, object],
    key: str,
    manifest_path: Path,
) -> dict[object, object]:
    value = parsed.get(key)
    if isinstance(value, dict):
        return typ.cast("dict[object, object]", value)
    msg = f"Invalid manifest section {key!r} in {manifest_path}: expected object"
    raise ManifestError(msg)


def _load_records(value: dict[object, object]) -> dict[str, ToolRecord]:
    records: dict[str, ToolRecord] = {}
    for name, record in value.items():
        if not isinstance(name, str):
            msg = f"Invalid manifest record name {name!r}: expected string"
            raise ManifestError(msg)
        if not isinstance(record, dict):
            msg = f"Invalid manifest record {name!r}: expected object"
            raise ManifestError(msg)
        record_data = typ.cast("dict[object, object]", record)
        try:
            records[name] = ToolRecord(
                source=_string_field(record_data, "source"),
                files=_string_tuple(record_data, "files"),
                ignore_patterns=_string_tuple(record_data, "ignore_patterns"),
            )
        except ManifestError as exc:
            msg = f"Invalid manifest record {name!r}: {exc}"
            raise ManifestError(msg) from exc
    return records


def _dump_manifest(manifest: Manifest) -> dict[str, object]:
    return {
        "mcps": _dump_records(manifest.mcps),
        "skills": _dump_records(manifest.skills),
    }


def _dump_records(records: dict[str, ToolRecord]) -> dict[str, object]:
    return {
        name: {
            "files": list(record.files),
            "ignore_patterns": list(record.ignore_patterns),
            "source": record.source,
        }
        for name, record in records.items()
    }


def _string_field(record: dict[object, object], key: str) -> str:
    value = record.get(key)
    if isinstance(value, str):
        return value
    msg = (
        f"Invalid manifest field {key!r}: expected string, found {type(value).__name__}"
    )
    raise ManifestError(msg)


def _string_tuple(record: dict[object, object], key: str) -> tuple[str, ...]:
    value = record.get(key)
    if not isinstance(value, list):
        msg = (
            f"Invalid manifest field {key!r}: expected list of strings, "
            f"found {type(value).__name__}"
        )
        raise ManifestError(msg)
    items: list[str] = []
    for item in value:
        if not isinstance(item, str):
            msg = (
                f"Invalid manifest field {key!r}: expected list of strings, "
                f"but found item {item!r} of type {type(item).__name__}"
            )
            raise ManifestError(msg)
        items.append(item)
    return tuple(items)
