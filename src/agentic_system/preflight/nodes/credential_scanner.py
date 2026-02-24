"""Pre-Flight Credential Scanner — agentic node backed by BaseAgent."""
from __future__ import annotations

import logging

from langchain_core.messages import HumanMessage
from langgraph.types import interrupt

from src.agentic_system.preflight.prompts.credential_scanner import CREDENTIAL_SCANNER_SYSTEM_PROMPT
from src.agentic_system.preflight.schemas.scanner_output import ScannerOutput
from src.agentic_system.preflight.tools import SCANNER_TOOLS
from src.agentic_system.shared.base_agent import BaseAgent
from src.agentic_system.shared.state import ARIAState

logger = logging.getLogger(__name__)

_scanner_agent: BaseAgent[ScannerOutput] = BaseAgent(
    prompt=CREDENTIAL_SCANNER_SYSTEM_PROMPT,
    schema=ScannerOutput,
    tools=SCANNER_TOOLS,
    name="CredentialScanner",
)


async def credential_scanner_node(state: ARIAState) -> dict:
    """Scan required node types against saved n8n credentials via the agent.

    Calls the CredentialScanner agent, handles HITL for ambiguous credentials,
    then returns resolved IDs, pending types, and a status message.
    """
    required_nodes: list[str] = state["required_nodes"]
    already_resolved: dict[str, str] = dict(state.get("resolved_credential_ids", {}))

    logger.info("[CredentialScanner] Scanning %d node type(s)", len(required_nodes))

    user_message = HumanMessage(
        content=f"Scan credentials for these node types: {required_nodes}"
    )
    result: ScannerOutput = await _scanner_agent.invoke([user_message])

    resolved = {**already_resolved, **result.resolved}
    pending = result.pending
    ambiguous = result.ambiguous

    if ambiguous:
        resolved = _apply_hitl_choices(resolved, ambiguous)
        pending = [t for t in pending if t not in resolved]

    status_msg = _build_status_message(pending, ambiguous, result.summary)
    logger.info("[CredentialScanner] %s", result.summary)

    return {
        "resolved_credential_ids": resolved,
        "pending_credential_types": pending,
        "paused_for_input": False,
        "messages": [HumanMessage(content=status_msg)],
    }


def _apply_hitl_choices(
    resolved: dict[str, str],
    ambiguous: dict[str, list[dict]],
) -> dict[str, str]:
    """Interrupt to let the user pick one credential per ambiguous type.

    Unified resume schema:
      {"action": "select", "selections": {"Gmail OAuth2": "<credential-id>"}}
    """
    response: dict = interrupt({
        "type": "credential_ambiguity",
        "paused_for_input": True,
        "ambiguous": {
            cred_type: [{"id": c["id"], "name": c.get("name", c["id"])} for c in candidates]
            for cred_type, candidates in ambiguous.items()
        },
        "message": "Multiple saved credentials found. Select one ID per type.",
    })
    selections: dict[str, str] = response.get("selections", {}) if isinstance(response, dict) else {}
    return {**resolved, **selections}


def _build_status_message(
    pending: list[str],
    ambiguous: dict[str, list[dict]],
    summary: str,
) -> str:
    if pending:
        return f"[Scanner] Missing credentials for: {', '.join(pending)}"
    if ambiguous:
        return f"[Scanner] Ambiguous credentials for: {', '.join(ambiguous)}"
    return f"[Scanner] All credentials resolved. {summary}"
