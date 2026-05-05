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
    parsed = json.loads(manifest_path.read_text())
    if not isinstance(parsed, dict):
        return Manifest(mcps={}, skills={})
    return Manifest(
        mcps=_load_records(parsed.get("mcps", {})),
        skills=_load_records(parsed.get("skills", {})),
    )


def save_manifest(repository: Path, manifest: Manifest) -> None:
    """Write the repo-local managed tool manifest."""
    manifest_path = repository / MANIFEST_PATH
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        f"{json.dumps(_dump_manifest(manifest), indent=2, sort_keys=True)}\n"
    )


def _load_records(value: object) -> dict[str, ToolRecord]:
    if not isinstance(value, dict):
        return {}
    records: dict[str, ToolRecord] = {}
    for name, record in value.items():
        if isinstance(name, str) and isinstance(record, dict):
            record_data = typ.cast("dict[object, object]", record)
            records[name] = ToolRecord(
                source=_string_field(record_data, "source"),
                files=_string_tuple(record_data, "files"),
                ignore_patterns=_string_tuple(record_data, "ignore_patterns"),
            )
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
    return value if isinstance(value, str) else ""


def _string_tuple(record: dict[object, object], key: str) -> tuple[str, ...]:
    value = record.get(key)
    if not isinstance(value, list):
        return ()
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
