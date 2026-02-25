"""Pipeline services — preflight (Phase 1) and build (Phase 2)."""

from __future__ import annotations


def __getattr__(name: str) -> object:
    """Lazily resolve pipeline sub-module exports."""
    if name == "run_preflight":
        from src.services.pipeline.preflight import run_preflight
        return run_preflight
    if name in ("run_build", "load_preflight_state"):
        from src.services.pipeline import build as _build
        return getattr(_build, name)
    raise AttributeError(f"module 'src.services.pipeline' has no attribute {name!r}")
