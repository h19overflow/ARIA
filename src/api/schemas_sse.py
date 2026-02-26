"""SSE event schema — split from schemas.py to respect the 150-line file limit."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class SSEEvent(BaseModel):
    type: Literal["node", "node_start", "interrupt", "done", "error", "ping"]
    stage: str | None = None
    node_name: str | None = None
    message: str | None = None
    status: str | None = None
    kind: str | None = None
    payload: dict | None = None
    aria_state: dict | None = None
    event_id: str | None = None
    tools: list[str] | None = None
    duration_ms: int | None = None
    timestamp: str | None = None
    progress: str | None = None
