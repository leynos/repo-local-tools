"""Shared exception types for user-facing agent tool failures."""

from __future__ import annotations


class AgentToolsError(Exception):
    """Base error for user-facing agent tool command failures."""
