"""Pipeline services — build (Phase 2)."""

from __future__ import annotations


def __getattr__(name: str) -> object:
    """Lazily resolve pipeline sub-module exports."""
    if name == "run_build":
        from src.services.pipeline import build as _build
        return getattr(_build, name)
    raise AttributeError(f"module 'src.services.pipeline' has no attribute {name!r}")
