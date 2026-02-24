"""Pure parsing helpers for n8n API responses."""
from __future__ import annotations

_KEEP_CRED_FIELDS = {"id", "name", "type"}


def parse_credentials(raw: list[dict]) -> list[dict]:
    """Normalize each credential to {id, name, type} only."""
    return [{k: item[k] for k in _KEEP_CRED_FIELDS if k in item} for item in raw]


def parse_credential_schema(raw: dict) -> dict:
    """Extract {required_fields, optional_fields} from a JSON Schema credential response."""
    properties: dict = raw.get("properties", {})
    required_set: set[str] = set(raw.get("required", []))
    props = [
        {
            "name": field_name,
            "type": field_def.get("type", "string") if isinstance(field_def, dict) else "string",
            "required": field_name in required_set,
            "description": field_def.get("description", "") if isinstance(field_def, dict) else "",
        }
        for field_name, field_def in properties.items()
        if field_name != "notice"
    ]
    return {
        "properties": props,
        "required": sorted(required_set - {"notice"}),
    }


def group_by_type(credentials: list[dict]) -> dict[str, list[dict]]:
    """Group normalized credentials by their type field."""
    result: dict[str, list[dict]] = {}
    for cred in credentials:
        cred_type = cred.get("type", "unknown")
        result.setdefault(cred_type, []).append(cred)
    return result
