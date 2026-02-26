"""Notes state mutation helpers for PreflightAgent."""
from __future__ import annotations

import json
import logging
from typing import Any, Dict

from .state import PreflightState

logger = logging.getLogger(__name__)


def update_notes_on_save_credential(
    state: PreflightState, tool_args: Dict[str, Any]
) -> None:
    """No-op: pending removal happens only after a successful result.

    Called at tool_start before the result is known — we intentionally
    do nothing here so a failed save doesn't silently drop the type.
    """


def update_notes_on_save_credential_result(
    state: PreflightState, tool_result: Any
) -> None:
    """Update resolved_credential_ids from a successful save_credential result."""
    try:
        data = json.loads(tool_result) if isinstance(tool_result, str) else tool_result
        if data.get("success") and data.get("id") and data.get("type"):
            cred_type = data["type"]
            state.notes.resolved_credential_ids[cred_type] = data["id"]
            state.notes.pending_credential_types = [
                t for t in state.notes.pending_credential_types
                if t != cred_type
            ]
    except (json.JSONDecodeError, AttributeError, KeyError) as e:
        logger.warning("Failed to parse save_credential result: %s", e)


def update_notes_on_commit(state: PreflightState, summary: str) -> None:
    """Mark preflight as committed with the provided summary."""
    state.notes.summary = summary
    state.notes.committed = True
    state.committed = True
