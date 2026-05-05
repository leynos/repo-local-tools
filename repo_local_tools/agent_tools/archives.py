"""Skill archive validation and extraction helpers."""

from __future__ import annotations

import shutil
import zipfile
from pathlib import Path, PurePosixPath

from repo_local_tools.agent_tools.errors import AgentToolsError


class ArchiveError(AgentToolsError):
    """Raised when a skill archive cannot be safely extracted."""


def extract_skill_archive(archive_path: Path, extract_root: Path) -> Path:
    """Extract an Anthropic `.skill` archive and return its skill directory."""
    if not archive_path.is_absolute():
        msg = "skill archive paths must be absolute"
        raise ArchiveError(msg)
    if not archive_path.exists():
        msg = f"skill archive does not exist: {archive_path}"
        raise ArchiveError(msg)
    if extract_root.exists():
        shutil.rmtree(extract_root)
    extract_root.mkdir(parents=True)

    try:
        with zipfile.ZipFile(archive_path) as archive:
            entries = [entry for entry in archive.infolist() if not entry.is_dir()]
            top_levels = {_validated_parts(entry.filename)[0] for entry in entries}
            if len(top_levels) != 1:
                msg = "skill archive must contain exactly one top-level directory"
                raise ArchiveError(msg)
            for entry in entries:
                parts = _validated_parts(entry.filename)
                target = extract_root.joinpath(*parts)
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(entry) as source, target.open("wb") as destination:
                    shutil.copyfileobj(source, destination)
    except zipfile.BadZipFile as error:
        msg = f"invalid skill archive: {archive_path}"
        raise ArchiveError(msg) from error

    return extract_root / next(iter(top_levels))


def _validated_parts(filename: str) -> tuple[str, ...]:
    path = PurePosixPath(filename)
    is_structurally_unsafe = path.is_absolute() or not path.parts
    has_parent_reference = ".." in path.parts
    if is_structurally_unsafe or has_parent_reference:
        msg = f"unsafe skill archive entry: {filename}"
        raise ArchiveError(msg)
    return path.parts
