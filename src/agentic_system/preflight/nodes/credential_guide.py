"""Pre-Flight Credential Guide -- enriches interrupt payload with per-credential guides.

Known credential types are resolved from a static map (zero LLM cost).
Unknown types fall back to a Gemini agent for prose generation.
Schema fields always come from n8n (ground truth).
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from langchain_core.messages import HumanMessage

from src.agentic_system.preflight.nodes._credential_guide_data import CREDENTIAL_GUIDES
from src.agentic_system.preflight.nodes._credential_guide_helpers import (
    build_llm_prompt,
    build_static_entry,
    build_summary,
    reorder_entries,
    validate_and_patch,
)
from src.agentic_system.preflight.prompts.credential_guide import CREDENTIAL_GUIDE_SYSTEM_PROMPT
from src.agentic_system.preflight.schemas.credential_guide import (
    CredentialGuideEntry,
    CredentialGuideOutput,
)
from src.agentic_system.shared.base_agent import BaseAgent
from src.agentic_system.shared.state import ARIAState
from src.boundary.n8n.client import N8nClient

log = logging.getLogger(__name__)

# Lazy-initialised -- only created when unknown credential types are encountered.
_guide_agent: BaseAgent[CredentialGuideOutput] | None = None


def _get_guide_agent() -> BaseAgent[CredentialGuideOutput]:
    """Return the LLM agent, creating it on first call."""
    global _guide_agent  # noqa: PLW0603
    if _guide_agent is None:
        _guide_agent = BaseAgent(
            prompt=CREDENTIAL_GUIDE_SYSTEM_PROMPT,
            schema=CredentialGuideOutput,
            tools=[],
            name="CredentialGuide",
            model_name="gemini-3-flash-preview",
            recursion_limit=8,
        )
    return _guide_agent


async def credential_guide_node(state: ARIAState) -> dict[str, Any]:
    """Build credential guides from static data (known) or LLM (unknown)."""
    pending = state.get("pending_credential_types", [])
    if not pending:
        return {}

    schemas = await _fetch_schemas_parallel(pending)
    known = [ct for ct in pending if ct in CREDENTIAL_GUIDES]
    unknown = [ct for ct in pending if ct not in CREDENTIAL_GUIDES]

    known_entries = [build_static_entry(ct, schemas.get(ct, {})) for ct in known]
    unknown_entries = await _resolve_unknown(unknown, schemas) if unknown else []

    all_entries = known_entries + unknown_entries
    ordered = reorder_entries(all_entries, pending)
    summary = build_summary(pending)
    result = CredentialGuideOutput(entries=ordered, summary=summary)
    return {"credential_guide_payload": result.model_dump()}


async def _fetch_schemas_parallel(pending: list[str]) -> dict[str, dict]:
    """Fetch credential schemas from n8n in parallel via asyncio.gather."""
    client = N8nClient()
    await client.connect()
    try:
        results = await asyncio.gather(
            *[_safe_fetch_schema(client, ct) for ct in pending]
        )
        return dict(zip(pending, results))
    finally:
        await client.disconnect()


async def _safe_fetch_schema(client: N8nClient, cred_type: str) -> dict:
    """Fetch a single schema, returning an empty fallback on failure."""
    try:
        return await client.get_credential_schema(cred_type)
    except Exception as exc:
        log.warning("Failed to fetch schema for %s: %s", cred_type, exc)
        return {"properties": [], "required": []}


async def _resolve_unknown(
    unknown: list[str], schemas: dict[str, dict],
) -> list[CredentialGuideEntry]:
    """Fall back to LLM agent for credential types not in the static map."""
    log.info("Using LLM fallback for unknown credential types: %s", unknown)
    prompt = build_llm_prompt(unknown, schemas)
    agent = _get_guide_agent()
    result: CredentialGuideOutput = await agent.invoke([HumanMessage(content=prompt)])
    result = validate_and_patch(result, unknown, schemas)
    return result.entries
