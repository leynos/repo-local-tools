"""Manifest parsing coverage for managed tool metadata."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from repo_local_tools.agent_tools.manifest import (
    MANIFEST_PATH,
    Manifest,
    ManifestError,
    ToolRecord,
    load_manifest,
    save_manifest,
)


def test_load_manifest_rejects_partially_invalid_string_lists(tmp_path: Path) -> None:
    manifest_path = tmp_path / MANIFEST_PATH
    manifest_path.parent.mkdir(parents=True)
    manifest_path.write_text(
        json.dumps(
            {
                "mcps": {
                    "echo": {
                        "files": [".mcp.json", 7],
                        "ignore_patterns": [".mcp.json"],
                        "source": str(tmp_path / "echo.toml"),
                    },
                },
                "skills": {},
            },
        ),
    )

    with pytest.raises(ManifestError, match="Invalid manifest field 'files'"):
        load_manifest(tmp_path)


def test_load_manifest_rejects_malformed_json(tmp_path: Path) -> None:
    manifest_path = tmp_path / MANIFEST_PATH
    manifest_path.parent.mkdir(parents=True)
    manifest_path.write_text("{")

    expected_message = re.escape(f"Invalid manifest JSON in {manifest_path}")
    with pytest.raises(ManifestError, match=expected_message):
        load_manifest(tmp_path)


def test_load_manifest_rejects_non_object_manifest(tmp_path: Path) -> None:
    manifest_path = tmp_path / MANIFEST_PATH
    manifest_path.parent.mkdir(parents=True)
    manifest_path.write_text("[]")

    with pytest.raises(ManifestError, match="expected top-level object"):
        load_manifest(tmp_path)


def test_load_manifest_rejects_invalid_sections(tmp_path: Path) -> None:
    manifest_path = tmp_path / MANIFEST_PATH
    manifest_path.parent.mkdir(parents=True)
    manifest_path.write_text(json.dumps({"mcps": [], "skills": {}}))

    with pytest.raises(ManifestError, match="Invalid manifest section 'mcps'"):
        load_manifest(tmp_path)


def test_load_manifest_rejects_malformed_records(tmp_path: Path) -> None:
    manifest_path = tmp_path / MANIFEST_PATH
    manifest_path.parent.mkdir(parents=True)
    manifest_path.write_text(json.dumps({"mcps": {"echo": []}, "skills": {}}))

    with pytest.raises(ManifestError, match="Invalid manifest record 'echo'"):
        load_manifest(tmp_path)


def test_save_manifest_replaces_manifest_without_tmp_file(tmp_path: Path) -> None:
    manifest = Manifest(
        mcps={
            "echo": ToolRecord(
                source="echo.toml",
                files=(".mcp.json",),
                ignore_patterns=(".mcp.json",),
            ),
        },
        skills={},
    )

    save_manifest(tmp_path, manifest)

    manifest_path = tmp_path / MANIFEST_PATH
    temporary_path = manifest_path.with_name(f"{manifest_path.name}.tmp")
    assert not temporary_path.exists(), (
        f"expected save_manifest to replace {manifest_path}, but found "
        f"temporary file {temporary_path}"
    )
    assert load_manifest(tmp_path).mcps["echo"].source == "echo.toml"
