"""Pure parsing helpers for n8n API responses."""
from __future__ import annotations

_KEEP_CRED_FIELDS = {"id", "name", "type"}


def parse_credentials(raw: list[dict]) -> list[dict]:
    """Normalize each credential to {id, name, type} only."""
    return [{k: item[k] for k in _KEEP_CRED_FIELDS if k in item} for item in raw]


def parse_credential_schema(raw: dict) -> dict:
    """Extract {properties, required, conditional_fields} from a JSON Schema credential response.

    Preserves enum lists so callers can avoid backfilling enum fields
    with invalid empty strings. Parses allOf if/then blocks to identify
    fields that must only appear when a boolean gate is True — these are
    marked conditional so backfill skips them when the gate is False.
    """
    properties: dict = raw.get("properties", {})
    required_set: set[str] = set(raw.get("required", []))
    conditional_fields: set[str] = _extract_conditional_fields(raw.get("allOf", []))

    props = []
    for field_name, field_def in properties.items():
        if not isinstance(field_def, dict):
            continue
        entry: dict = {
            "name": field_name,
            "type": field_def.get("type", "string"),
            "required": field_name in required_set,
            "description": field_def.get("description", ""),
            "conditional": field_name in conditional_fields,
        }
        if "enum" in field_def:
            entry["enum"] = field_def["enum"]
        props.append(entry)
    return {
        "properties": props,
        "required": sorted(required_set),
    }


def _extract_conditional_fields(all_of: list) -> set[str]:
    """Collect fields that only appear inside allOf if/then branches.

    These must NOT be backfilled with empty defaults — n8n prohibits them
    when their gating condition is false.
    """
    conditional: set[str] = set()
    for clause in all_of:
        then_block = clause.get("then", {})
        for sub in then_block.get("allOf", []):
            for field in sub.get("required", []):
                conditional.add(field)
        for field in then_block.get("required", []):
            conditional.add(field)
    return conditional


def group_by_type(credentials: list[dict]) -> dict[str, list[dict]]:
    """Group normalized credentials by their type field."""
    result: dict[str, list[dict]] = {}
    for cred in credentials:
        cred_type = cred.get("type", "unknown")
        result.setdefault(cred_type, []).append(cred)
    return result
