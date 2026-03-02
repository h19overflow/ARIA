"""Fan-out logic for dispatching NodeSpecs to parallel workers."""
from __future__ import annotations

from langgraph.types import Send

from src.agentic_system.shared.state import ARIAState


def fan_out_nodes(state: ARIAState) -> list[Send]:
    """Fan out NodeSpec list to parallel workers via Send API."""
    nodes_to_build = state.get("nodes_to_build", [])
    if not nodes_to_build:
        return []
    return [
        Send("node_worker", {
            "node_spec": spec,
            "resolved_credential_ids": state.get("resolved_credential_ids", {}),
            "job_id": state.get("job_id", ""),
        })
        for spec in nodes_to_build
    ]
