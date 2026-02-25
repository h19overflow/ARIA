"""Pre-Flight Credential Guide -- enriches interrupt payload with per-credential guides.

Fetches n8n credential schemas deterministically, injects them into the LLM
prompt as ground truth, then validates the output covers all pending types.
"""
from __future__ import annotations

import json
import logging

from langchain_core.messages import HumanMessage

from src.agentic_system.preflight.prompts.credential_guide import CREDENTIAL_GUIDE_SYSTEM_PROMPT
from src.agentic_system.preflight.schemas.credential_guide import (
    CredentialFieldInfo,
    CredentialGuideEntry,
    CredentialGuideOutput,
)
from src.agentic_system.preflight.tools.rag_tools import search_n8n_nodes
from src.agentic_system.shared.base_agent import BaseAgent
from src.agentic_system.shared.state import ARIAState
from src.boundary.n8n.client import N8nClient

log = logging.getLogger(__name__)

# Agent only generates prose (how_to_obtain, help_url, service_description).
# Field data comes from n8n schemas injected into the prompt — no tool needed.
_guide_agent: BaseAgent[CredentialGuideOutput] = BaseAgent(
    prompt=CREDENTIAL_GUIDE_SYSTEM_PROMPT,
    schema=CredentialGuideOutput,
    tools=[search_n8n_nodes],
    name="CredentialGuide",
)


async def credential_guide_node(state: ARIAState) -> dict:
    """Fetch schemas from n8n, generate prose via LLM, validate coverage."""
    pending = state.get("pending_credential_types", [])
    if not pending:
        return {}

    schemas = await _fetch_schemas(pending)
    prompt = _build_prompt(pending, schemas)
    result: CredentialGuideOutput = await _guide_agent.invoke([HumanMessage(content=prompt)])
    result = _validate_and_patch(result, pending, schemas)
    return {"credential_guide_payload": result.model_dump()}


async def _fetch_schemas(pending: list[str]) -> dict[str, dict]:
    """Fetch credential schemas from n8n for each pending type."""
    client = N8nClient()
    await client.connect()
    schemas: dict[str, dict] = {}
    try:
        for cred_type in pending:
            try:
                schemas[cred_type] = await client.get_credential_schema(cred_type)
            except Exception as exc:
                log.warning("Failed to fetch schema for %s: %s", cred_type, exc)
                schemas[cred_type] = {"properties": [], "required": []}
    finally:
        await client.disconnect()
    return schemas


def _build_prompt(pending: list[str], schemas: dict[str, dict]) -> str:
    """Build an LLM prompt with ground-truth schema data."""
    schema_blocks = []
    for cred_type in pending:
        schema = schemas.get(cred_type, {})
        props = schema.get("properties", [])
        field_summary = json.dumps(props, indent=2) if props else "[]"
        schema_blocks.append(
            f"### {cred_type}\n"
            f"Fields (from n8n — do NOT invent others):\n```json\n{field_summary}\n```"
        )

    return (
        f"Generate a guide for these credential types: {pending}\n\n"
        f"## Ground-truth schemas (fetched from n8n)\n\n"
        + "\n\n".join(schema_blocks)
        + "\n\nUse ONLY the fields listed above for each credential type. "
        "Focus on writing helpful how_to_obtain steps, a real help_url, "
        "and a clear service_description."
    )


def _validate_and_patch(
    result: CredentialGuideOutput,
    pending: list[str],
    schemas: dict[str, dict],
) -> CredentialGuideOutput:
    """Ensure every pending type has an entry with correct fields."""
    entries_by_type = {e.credential_type: e for e in result.entries}

    for cred_type in pending:
        schema = schemas.get(cred_type, {})
        ground_truth_fields = _fields_from_schema(schema)

        if cred_type not in entries_by_type:
            log.warning("LLM missed entry for %s — patching with deterministic fallback", cred_type)
            entries_by_type[cred_type] = _fallback_entry(cred_type, ground_truth_fields)
        else:
            # Override fields with ground truth — LLM prose stays, fields are deterministic
            entries_by_type[cred_type] = entries_by_type[cred_type].model_copy(
                update={"fields": ground_truth_fields}
            )

    patched = [entries_by_type[ct] for ct in pending]
    return result.model_copy(update={"entries": patched})


def _fields_from_schema(schema: dict) -> list[CredentialFieldInfo]:
    """Convert n8n schema properties to CredentialFieldInfo list."""
    return [
        CredentialFieldInfo(
            name=p["name"],
            label=p.get("name", "").replace("_", " ").title(),
            description=p.get("description", ""),
            required=p.get("required", False),
        )
        for p in schema.get("properties", [])
    ]


def _fallback_entry(cred_type: str, fields: list[CredentialFieldInfo]) -> CredentialGuideEntry:
    """Deterministic fallback when the LLM skips a credential type entirely."""
    display = cred_type.replace("Api", " API").replace("OAuth2", " OAuth2")
    return CredentialGuideEntry(
        credential_type=cred_type,
        display_name=display,
        service_description=f"Credentials for {display}.",
        how_to_obtain="1. Visit the service's developer portal.\n2. Create or locate your API credentials.",
        help_url="",
        fields=fields,
    )
