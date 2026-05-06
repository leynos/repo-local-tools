"""Path resolution helpers for repo-local-tools."""

from __future__ import annotations

import os
from pathlib import Path


def current_repository() -> Path:
    """Return the repository targeted by the current command invocation."""
    return Path.cwd()


def data_root(xdg_data_home: Path | None) -> Path:
    """Return the repo-local-tools data root under XDG data home."""
    if xdg_data_home is not None:
        return xdg_data_home / "repo-local-tools"
    configured_home = os.environ.get("XDG_DATA_HOME")
    if configured_home:
        return Path(configured_home) / "repo-local-tools"
    return Path.home() / ".local" / "share" / "repo-local-tools"
