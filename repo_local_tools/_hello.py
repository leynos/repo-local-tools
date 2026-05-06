"""Optional Rust-backed hello implementation."""

from __future__ import annotations

try:  # pragma: no cover - Rust optional
    rust = __import__("_repo_local_tools_rs")
    hello = rust.hello  # type: ignore[attr-defined]
except ModuleNotFoundError:  # pragma: no cover - Python fallback
    from repo_local_tools.pure import hello

__all__ = ["hello"]
