"""Manifest parsing coverage for managed tool metadata."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from repo_local_tools.agent_tools.manifest import (
    MANIFEST_PATH,
    ManifestError,
    load_manifest,
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
