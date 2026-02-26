"""LangChain tools for ARIA Phase 1 — Preflight Agent."""
from __future__ import annotations

import json
import logging

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from src.boundary.n8n.client import N8nClient
from src.agentic_system.shared.node_credential_map import NODE_CREDENTIAL_MAP
from .schema_helpers import fetch_pending_details, fields_from_schema

logger = logging.getLogger(__name__)


class SaveCredentialInput(BaseModel):
    credential_type: str = Field(
        description="The n8n credential type identifier, e.g. 'telegramApi', 'openAiApi'"
    )
    name: str = Field(
        description="A human-readable name for this credential in n8n, e.g. 'My Telegram Bot'"
    )
    data: dict = Field(
        description="Key-value pairs of credential fields required by the credential type"
    )


class CommitPreflightInput(BaseModel):
    summary: str = Field(
        description="One-line summary of what was resolved, e.g. 'All 3 credentials saved'"
    )


def make_scan_credentials(required_nodes: list[str]):
    """Create a scan_credentials tool bound to the required node types."""

    @tool("scan_credentials")
    async def scan_credentials() -> str:
        """Check n8n for already-saved credentials for the required integrations.

        Returns JSON: {"resolved": [...], "pending": [...], "pending_details": {...}}
        - resolved: credentials already saved in n8n that match required types
        - pending: required credential types not yet saved
        - pending_details: field schemas for each pending type (use these to ask the user)
        Always call this FIRST at the start of every preflight session.
        """
        client = N8nClient()
        await client.connect()
        try:
            saved = await client.list_credentials()
            resolved, pending = _classify_credentials(saved, required_nodes)
        except Exception as e:
            logger.error("scan_credentials failed: %s", e)
            return json.dumps({"error": str(e), "resolved": [], "pending": []})
        finally:
            await client.disconnect()

        pending_details = await fetch_pending_details(pending)
        return json.dumps({"resolved": resolved, "pending": pending, "pending_details": pending_details})

    return scan_credentials


def _classify_credentials(
    saved: list[dict], required_nodes: list[str]
) -> tuple[list[dict], list[str]]:
    """Split saved credentials into resolved/pending against required_nodes."""
    saved_types = {c.get("type", "") for c in saved}
    resolved = []
    pending = []
    for node_key in required_nodes:
        cred_types = NODE_CREDENTIAL_MAP.get(node_key, [])
        if not cred_types:
            continue  # node needs no credentials (e.g. webhook)
        if any(ct in saved_types for ct in cred_types):
            matches = [c for c in saved if c.get("type", "") in cred_types]
            resolved.extend(matches)
        else:
            pending.append(cred_types[0])
    return resolved, pending


@tool("get_credential_schema")
async def get_credential_schema(credential_type: str) -> str:
    """Fetch the live field schema for a credential type from n8n.

    Returns JSON: {
      "credential_type": str,
      "fields": [{"name": str, "required": bool, "is_secret": bool, "description": str}]
    }
    Call this before asking the user for a credential to know exactly what fields to request.
    Use when pending_details is missing a type or you need to confirm field names.
    """
    client = N8nClient()
    await client.connect()
    try:
        schema = await client.get_credential_schema(credential_type)
    except Exception as e:
        logger.error("get_credential_schema failed type=%s: %s", credential_type, e)
        return json.dumps({"error": str(e), "credential_type": credential_type, "fields": []})
    finally:
        await client.disconnect()

    return json.dumps({"credential_type": credential_type, "fields": fields_from_schema(schema)})


@tool("save_credential", args_schema=SaveCredentialInput)
async def save_credential(credential_type: str, name: str, data: dict) -> str:
    """Save one credential to n8n and return its ID.

    Call once per credential type after the user provides the required field values.
    Returns the credential ID on success, or an error message on failure.
    """
    client = N8nClient()
    await client.connect()
    try:
        result = await client.save_credential(credential_type, name, data)
        credential_id = result.get("id", "")
        logger.info("Saved credential type=%s name=%s id=%s", credential_type, name, credential_id)
        return json.dumps({"success": True, "id": credential_id, "type": credential_type, "name": name})
    except Exception as e:
        logger.error("save_credential failed type=%s: %s", credential_type, e)
        return json.dumps({"success": False, "error": str(e)})
    finally:
        await client.disconnect()


@tool("commit_preflight", args_schema=CommitPreflightInput)
async def commit_preflight(summary: str) -> str:
    """Finalize the preflight phase.

    Call when ALL required credential types are resolved. Marks preflight as complete
    and enables the user to proceed to the build phase.
    """
    logger.info("commit_preflight called: %s", summary)
    return json.dumps({"committed": True, "summary": summary})
