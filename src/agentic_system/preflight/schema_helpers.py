"""Credential schema helpers for the Preflight Agent."""
from __future__ import annotations

import asyncio
import logging

from src.boundary.n8n.client import N8nClient

logger = logging.getLogger(__name__)

_SECRET_KEYWORDS = frozenset({"token", "key", "secret", "password", "auth", "credential"})


def is_secret_field(name: str) -> bool:
    """Return True if the field name suggests it holds a sensitive value."""
    lower = name.lower()
    return any(kw in lower for kw in _SECRET_KEYWORDS)


def fields_from_schema(schema: dict) -> list[dict]:
    """Convert a parsed n8n credential schema into a list of field descriptors."""
    return [
        {
            "name": p["name"],
            "required": p["required"],
            "is_secret": is_secret_field(p["name"]),
            "description": p.get("description", ""),
        }
        for p in schema.get("properties", [])
        if not p.get("conditional")
    ]


async def fetch_pending_details(pending_types: list[str]) -> dict:
    """Fetch live field schemas for each pending credential type concurrently."""
    if not pending_types:
        return {}
    client = N8nClient()
    await client.connect()
    try:
        schemas = await asyncio.gather(
            *[client.get_credential_schema(ct) for ct in pending_types],
            return_exceptions=True,
        )
    finally:
        await client.disconnect()

    result: dict = {}
    for ct, schema in zip(pending_types, schemas):
        if isinstance(schema, Exception):
            logger.warning("Failed to fetch schema for %s: %s", ct, schema)
            result[ct] = []
        else:
            result[ct] = fields_from_schema(schema)
    return result
