"""Pure-Python fallback implementations for repo-local-tools.

This module contains platform-independent implementations used when native,
compiled, or optimized alternatives are unavailable. The package imports these
fallbacks automatically when optional native modules cannot be loaded, so
callers can use the public API without caring which implementation is active.

Example:
    from repo_local_tools.pure import hello

    greeting = hello()

"""

from __future__ import annotations


def hello() -> str:
    """Return a friendly greeting from Python."""
    return "hello from Python"
