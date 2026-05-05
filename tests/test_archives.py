from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from repo_local_tools.agent_tools.archives import ArchiveError, extract_skill_archive


def test_extract_skill_archive_requires_absolute_path(tmp_path: Path) -> None:
    with pytest.raises(ArchiveError, match="absolute"):
        extract_skill_archive(Path("relative.skill"), tmp_path / "extract")


def test_extract_skill_archive_nonexistent_path(tmp_path: Path) -> None:
    archive = tmp_path / "nonexistent.skill"

    with pytest.raises(ArchiveError, match="skill archive does not exist"):
        extract_skill_archive(archive, tmp_path / "extract")


def test_extract_skill_archive_corrupt_archive(tmp_path: Path) -> None:
    archive = tmp_path / "corrupt.skill"
    archive.write_text("this is not a zip file")

    with pytest.raises(ArchiveError, match="invalid skill archive"):
        extract_skill_archive(archive, tmp_path / "extract")


def test_extract_skill_archive_multiple_top_level_dirs(tmp_path: Path) -> None:
    archive = tmp_path / "multi_root.skill"
    with zipfile.ZipFile(archive, "w") as skill_archive:
        skill_archive.writestr("a/SKILL.md", "content a")
        skill_archive.writestr("b/SKILL.md", "content b")

    with pytest.raises(
        ArchiveError, match="must contain exactly one top-level directory"
    ):
        extract_skill_archive(archive, tmp_path / "extract")


def test_extract_skill_archive_rejects_escaping_entries(tmp_path: Path) -> None:
    archive = tmp_path / "unsafe.skill"
    with zipfile.ZipFile(archive, "w") as skill_archive:
        skill_archive.writestr("../escape/SKILL.md", "bad")

    with pytest.raises(ArchiveError, match="unsafe"):
        extract_skill_archive(archive, tmp_path / "extract")


def test_extract_skill_archive_returns_single_top_level_directory(
    tmp_path: Path,
) -> None:
    archive = tmp_path / "reviewer.skill"
    with zipfile.ZipFile(archive, "w") as skill_archive:
        skill_archive.writestr("reviewer/SKILL.md", "Use evidence.\n")

    extracted = extract_skill_archive(archive, tmp_path / "extract")

    assert extracted == tmp_path / "extract" / "reviewer"
    assert (extracted / "SKILL.md").read_text() == "Use evidence.\n"
