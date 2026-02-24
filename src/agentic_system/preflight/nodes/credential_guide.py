"""Pre-Flight Credential Guide -- enriches interrupt payload with per-credential guides."""
from __future__ import annotations

from langchain_core.messages import HumanMessage

from src.agentic_system.preflight.prompts.credential_guide import CREDENTIAL_GUIDE_SYSTEM_PROMPT
from src.agentic_system.preflight.schemas.credential_guide import CredentialGuideOutput
from src.agentic_system.preflight.tools.n8n_tools import get_credential_schema
from src.agentic_system.preflight.tools.rag_tools import search_n8n_nodes
from src.agentic_system.shared.base_agent import BaseAgent
from src.agentic_system.shared.state import ARIAState

_guide_agent: BaseAgent[CredentialGuideOutput] = BaseAgent(
    prompt=CREDENTIAL_GUIDE_SYSTEM_PROMPT,
    schema=CredentialGuideOutput,
    tools=[get_credential_schema, search_n8n_nodes],
    name="CredentialGuide",
)


async def credential_guide_node(state: ARIAState) -> dict:
    """Research each pending credential type and write a human-readable guide to state."""
    pending = state.get("pending_credential_types", [])
    if not pending:
        return {}

    message = HumanMessage(content=f"Generate a guide for these credential types: {pending}")
    result: CredentialGuideOutput = await _guide_agent.invoke([message])
    return {"credential_guide_payload": result.model_dump()}
