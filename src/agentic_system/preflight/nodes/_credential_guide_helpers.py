"""Helper functions for credential guide node -- schema parsing, LLM fallback, validation."""
from __future__ import annotations

import json
import logging

from src.agentic_system.preflight.nodes._credential_guide_data import CREDENTIAL_GUIDES
from src.agentic_system.preflight.schemas.credential_guide import (
    CredentialFieldInfo,
    CredentialGuideEntry,
    CredentialGuideOutput,
)

log = logging.getLogger(__name__)


def fields_from_schema(schema: dict) -> list[CredentialFieldInfo]:
    """Convert n8n schema properties to CredentialFieldInfo list."""
    fields: list[CredentialFieldInfo] = []
    for p in schema.get("properties", []):
        fields.append(CredentialFieldInfo(
            name=p["name"],
            label=p.get("name", "").replace("_", " ").title(),
            description=p.get("description", ""),
            required=p.get("required", False),
            options=p.get("enum"),
        ))
    return fields


def build_static_entry(cred_type: str, schema: dict) -> CredentialGuideEntry:
    """Build a guide entry from the static map + n8n schema fields."""
    guide = CREDENTIAL_GUIDES[cred_type]
    return CredentialGuideEntry(
        credential_type=cred_type,
        display_name=guide["display_name"],
        service_description=guide["service_description"],
        how_to_obtain=guide["how_to_obtain"],
        help_url=guide["help_url"],
        fields=fields_from_schema(schema),
    )


def build_llm_prompt(pending: list[str], schemas: dict[str, dict]) -> str:
    """Build an LLM prompt with ground-truth schema data."""
    blocks = []
    for cred_type in pending:
        props = schemas.get(cred_type, {}).get("properties", [])
        field_json = json.dumps(props, indent=2) if props else "[]"
        blocks.append(
            f"### {cred_type}\n"
            f"Fields (from n8n -- do NOT invent others):\n```json\n{field_json}\n```"
        )
    header = f"Generate a guide for these credential types: {pending}\n\n"
    body = "## Ground-truth schemas (fetched from n8n)\n\n" + "\n\n".join(blocks)
    footer = ("\n\nUse ONLY the fields listed above for each credential type. "
              "Focus on writing helpful how_to_obtain steps, a real help_url, "
              "and a clear service_description.")
    return header + body + footer


def build_summary(pending: list[str]) -> str:
    """Build a human-readable summary of all required credentials."""
    names = [CREDENTIAL_GUIDES.get(ct, {}).get("display_name", ct) for ct in pending]
    return f"You need to provide credentials for: {', '.join(names)}."


def reorder_entries(
    entries: list[CredentialGuideEntry], pending: list[str],
) -> list[CredentialGuideEntry]:
    """Return entries in the same order as the pending list."""
    by_type = {e.credential_type: e for e in entries}
    return [by_type[ct] for ct in pending if ct in by_type]


def validate_and_patch(
    result: CredentialGuideOutput,
    pending: list[str],
    schemas: dict[str, dict],
) -> CredentialGuideOutput:
    """Ensure every pending type has an entry with correct fields."""
    entries_by_type = {e.credential_type: e for e in result.entries}
    for cred_type in pending:
        ground_truth = fields_from_schema(schemas.get(cred_type, {}))
        if cred_type not in entries_by_type:
            log.warning("LLM missed %s -- using fallback", cred_type)
            entries_by_type[cred_type] = fallback_entry(cred_type, ground_truth)
        else:
            entries_by_type[cred_type] = entries_by_type[cred_type].model_copy(
                update={"fields": ground_truth},
            )
    patched = [entries_by_type[ct] for ct in pending]
    return result.model_copy(update={"entries": patched})


def fallback_entry(
    cred_type: str, fields: list[CredentialFieldInfo],
) -> CredentialGuideEntry:
    """Deterministic fallback when the LLM skips a credential type."""
    display = cred_type.replace("Api", " API").replace("OAuth2", " OAuth2")
    return CredentialGuideEntry(
        credential_type=cred_type,
        display_name=display,
        service_description=f"Credentials for {display}.",
        how_to_obtain="1. Visit the service's developer portal.\n2. Create or locate your API credentials.",
        help_url="",
        fields=fields,
    )
