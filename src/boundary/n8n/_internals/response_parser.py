"""Pure parsing helpers for n8n API responses."""
from __future__ import annotations

_KEEP_CRED_FIELDS = {"id", "name", "type"}


def parse_credentials(raw: list[dict]) -> list[dict]:
    """Normalize each credential to {id, name, type} only."""
    return [{k: item[k] for k in _KEEP_CRED_FIELDS if k in item} for item in raw]


def parse_credential_schema(raw: dict) -> dict:
    """Extract {type, displayName, properties} from a schema response."""
    props = [
        {
            "name": p.get("name", ""),
            "type": p.get("type", ""),
            "required": p.get("required", False),
            "description": p.get("description", ""),
        }
        for p in raw.get("properties", [])
    ]
    return {
        "type": raw.get("name", ""),
        "displayName": raw.get("displayName", ""),
        "properties": props,
    }


def group_by_type(credentials: list[dict]) -> dict[str, list[dict]]:
    """Group normalized credentials by their type field."""
    result: dict[str, list[dict]] = {}
    for cred in credentials:
        cred_type = cred.get("type", "unknown")
        result.setdefault(cred_type, []).append(cred)
    return result
