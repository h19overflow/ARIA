"""Deterministic credential resolver — matches NodeSpec node types to saved credentials."""
from __future__ import annotations

import logging

from src.agentic_system.shared.node_credential_map import NODE_CREDENTIAL_MAP

log = logging.getLogger(__name__)

_SHORT_KEY_ALIASES: dict[str, str] = {
    "lmChatGoogleGemini": "googleGemini",
    "lmChatOpenAi": "openAi",
    "lmOpenAi": "openAi",
    "lmChatAnthropic": "anthropicApi",
}


def resolve_node_credentials(
    nodes_to_build: list[dict],
    resolved_credential_ids: dict[str, str],
) -> list[dict]:
    """Attach credential_id and credential_type to each NodeSpec deterministically.

    For each node, extract the short key from node_type (e.g. 'gmail' from
    'n8n-nodes-base.gmail'), look it up in NODE_CREDENTIAL_MAP, and match
    against resolved_credential_ids.

    If no deterministic match, keep whatever the LLM set (fallback).
    """
    for spec in nodes_to_build:
        short_key = extract_short_key(spec.get("node_type", ""))
        credential_types = NODE_CREDENTIAL_MAP.get(short_key, [])
        matched = find_matching_credential(credential_types, resolved_credential_ids)

        if matched:
            cred_type, cred_id = matched
            log.info(
                "Credential resolved: %s → %s (id=%s)",
                spec.get("node_name"), cred_type, cred_id,
            )
            spec["credential_type"] = cred_type
            spec["credential_id"] = cred_id
        elif spec.get("credential_id") and spec.get("credential_type"):
            log.debug(
                "Keeping LLM-assigned credential for %s: type=%s id=%s",
                spec.get("node_name"), spec.get("credential_type"), spec.get("credential_id"),
            )

    return nodes_to_build


def extract_short_key(node_type: str) -> str:
    """Extract short node key from full n8n type string, applying aliases."""
    raw = node_type.rsplit(".", maxsplit=1)[-1] if "." in node_type else node_type
    return _SHORT_KEY_ALIASES.get(raw, raw)


def find_matching_credential(
    credential_types: list[str],
    resolved_credential_ids: dict[str, str],
) -> tuple[str, str] | None:
    """Find the first credential type that exists in resolved_credential_ids."""
    for cred_type in credential_types:
        cred_id = resolved_credential_ids.get(cred_type)
        if cred_id:
            return cred_type, cred_id
    return None
