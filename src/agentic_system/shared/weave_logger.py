"""Centralized Weave (W&B) logger — call ensure_weave_init() once at startup."""
from __future__ import annotations

import weave

from src.api.settings import settings

_initialized: bool = False


def ensure_weave_init() -> None:
    """Initialize Weave once. Safe to call multiple times."""
    global _initialized
    if _initialized:
        return
    weave.init(settings.wandb_project)
    _initialized = True
