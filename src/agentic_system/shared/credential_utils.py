"""Pure helpers for credential classification — shared by scanner node and tools."""
from __future__ import annotations


def group_by_type(credentials: list[dict]) -> dict[str, list[dict]]:
    """Group credential dicts by their 'type' field."""
    grouped: dict[str, list[dict]] = {}
    for cred in credentials:
        grouped.setdefault(cred.get("type", ""), []).append(cred)
    return grouped


def classify_node_credentials(
    cred_types: list[str],
    saved_by_type: dict[str, list[dict]],
    resolved: dict[str, str],
    pending: list[str],
    ambiguous: dict[str, list[dict]],
) -> None:
    """Classify a single node's credential types into resolved/pending/ambiguous.

    Mutates resolved, pending, and ambiguous in place.
    """
    for cred_type in cred_types:
        candidates = saved_by_type.get(cred_type, [])
        if len(candidates) == 1:
            resolved[cred_type] = candidates[0]["id"]
            return
        if len(candidates) > 1:
            ambiguous[cred_type] = candidates
            return
    pending.append(cred_types[0])


def fuzzy_match_credential_types(
    node_type: str, all_types: list[dict],
) -> list[str]:
    """Return credential type names whose displayName contains node_type (case-insensitive)."""
    needle = node_type.lower()
    return [
        t["name"]
        for t in all_types
        if needle in t.get("displayName", "").lower() and "name" in t
    ]
