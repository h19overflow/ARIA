"""LangChain tools for ARIA preflight agents — credential discovery and resolution."""
from __future__ import annotations

import json

import httpx
from langchain_core.tools import tool

from src.agentic_system.shared.node_credential_map import get_credential_types
from src.boundary.n8n.client import N8nClient


@tool
async def lookup_node_credential_types(node_type: str) -> str:
    """Return the credential types required by an n8n node type.

    First checks the static NODE_CREDENTIAL_MAP. Falls back to the n8n API
    and fuzzy-matches node_type against credential type displayNames.
    Returns JSON: {"node_type", "credential_types": [...], "source": "map"|"api"}.
    """
    from src.agentic_system.shared.node_credential_map import NODE_CREDENTIAL_MAP
    if node_type in NODE_CREDENTIAL_MAP:
        return json.dumps({"node_type": node_type, "credential_types": get_credential_types(node_type), "source": "map"})

    client = N8nClient()
    await client.connect()
    try:
        all_types = await client.list_credential_types()
    except httpx.HTTPStatusError as e:
        return json.dumps({"error": str(e)})
    finally:
        await client.disconnect()

    matched = _fuzzy_match_credential_types(node_type, all_types)
    return json.dumps({"node_type": node_type, "credential_types": matched, "source": "api"})


@tool
async def list_saved_credentials() -> str:
    """List all credentials saved in n8n. Returns JSON: {"count": N, "credentials": [{id, name, type}, ...]}."""
    client = N8nClient()
    await client.connect()
    try:
        credentials = await client.list_credentials()
    except httpx.HTTPStatusError as e:
        return json.dumps({"error": str(e)})
    finally:
        await client.disconnect()

    slim = [{"id": c["id"], "name": c.get("name", ""), "type": c.get("type", "")} for c in credentials]
    return json.dumps({"count": len(slim), "credentials": slim})


@tool
async def get_credential_schema(credential_type: str) -> str:
    """Fetch the field schema for an n8n credential type. Returns JSON:
    {"type", "displayName", "required_fields": [...], "all_fields": [...]}.
    """
    client = N8nClient()
    await client.connect()
    try:
        schema = await client.get_credential_schema(credential_type)
    except httpx.HTTPStatusError as e:
        return json.dumps({"error": str(e)})
    finally:
        await client.disconnect()

    properties = schema.get("properties", [])
    all_fields = [p["name"] for p in properties if "name" in p]
    required_fields = [p["name"] for p in properties if p.get("required") and "name" in p]
    return json.dumps({
        "type": schema.get("type", credential_type),
        "displayName": schema.get("displayName", ""),
        "required_fields": required_fields,
        "all_fields": all_fields,
    })


@tool
async def check_credentials_resolved(node_types: list[str]) -> str:
    """Diff required credential types against saved n8n credentials for a list of node types.

    Returns JSON: {"resolved": {cred_type: cred_id}, "pending": [cred_type,...],
    "ambiguous": {cred_type: [{id, name}, ...]}}. Ambiguous = >1 saved match.
    """
    client = N8nClient()
    await client.connect()
    try:
        saved = await client.list_credentials()
    except httpx.HTTPStatusError as e:
        return json.dumps({"error": str(e)})
    finally:
        await client.disconnect()

    saved_by_type = _group_by_type(saved)
    resolved: dict[str, str] = {}
    pending: list[str] = []
    ambiguous: dict[str, list[dict]] = {}

    for node_type in node_types:
        cred_types = get_credential_types(node_type)
        if not cred_types:
            continue
        if any(ct in resolved for ct in cred_types):
            continue
        _classify_node_credentials(cred_types, saved_by_type, resolved, pending, ambiguous)

    return json.dumps({
        "resolved": resolved,
        "pending": pending,
        "ambiguous": {ct: [{"id": c["id"], "name": c.get("name", "")} for c in cs]
                      for ct, cs in ambiguous.items()},
    })


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _fuzzy_match_credential_types(node_type: str, all_types: list[dict]) -> list[str]:
    """Return credential type names whose displayName contains node_type (case-insensitive)."""
    needle = node_type.lower()
    return [t["name"] for t in all_types if needle in t.get("displayName", "").lower() and "name" in t]


def _group_by_type(credentials: list[dict]) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = {}
    for cred in credentials:
        grouped.setdefault(cred.get("type", ""), []).append(cred)
    return grouped


def _classify_node_credentials(
    cred_types: list[str],
    saved_by_type: dict[str, list[dict]],
    resolved: dict[str, str],
    pending: list[str],
    ambiguous: dict[str, list[dict]],
) -> None:
    for cred_type in cred_types:
        candidates = saved_by_type.get(cred_type, [])
        if len(candidates) == 1:
            resolved[cred_type] = candidates[0]["id"]
            return
        if len(candidates) > 1:
            ambiguous[cred_type] = candidates
            return
    pending.append(cred_types[0])
