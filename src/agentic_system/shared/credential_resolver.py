"""Dynamic credential type resolver for n8n integrations.

Resolution chain:
1. INTEGRATION_ALIASES (from agent.py)
2. NODE_CREDENTIAL_MAP (hardcoded fast path)
3. Convention guessing + n8n API validation
4. LLM fallback (BaseAgent structured output)
5. Skip with warning
"""
import logging

import httpx

from src.api.settings import settings
from src.agentic_system.shared.node_credential_map import (
    INTEGRATION_ALIASES,
    NODE_CREDENTIAL_MAP,
)
from src.agentic_system.shared.credential_llm_fallback import llm_resolve

logger = logging.getLogger(__name__)

# Populated by successful convention guesses and LLM resolutions.
# Persists for the server lifetime — each integration resolved once.
_runtime_cache: dict[str, list[str]] = {}


def _normalize_to_camel_case(name: str) -> str:
    """Convert 'google sheets' or 'my-service' to 'googleSheets' / 'myService'."""
    parts = name.strip().replace("-", " ").split()
    if not parts:
        return ""
    # Single token that already has internal capitals — preserve as-is
    if len(parts) == 1 and any(c.isupper() for c in parts[0][1:]):
        return parts[0][0].lower() + parts[0][1:]
    return parts[0].lower() + "".join(p.capitalize() for p in parts[1:])


def _generate_candidates(camel_name: str) -> list[str]:
    """Generate candidate credential type names from a camelCase node name."""
    return [
        f"{camel_name}Api",
        f"{camel_name}OAuth2Api",
        f"{camel_name}OAuth2",
    ]


async def _validate_credential_type(credential_type: str) -> bool:
    """Check if a credential type exists in n8n by hitting the schema endpoint."""
    url = (
        f"{settings.n8n_base_url.rstrip('/')}"
        f"/api/v1/credentials/schema/{credential_type}"
    )
    headers = {"X-N8N-API-KEY": settings.n8n_api_key}
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(url, headers=headers)
            return resp.status_code == 200
    except httpx.HTTPError:
        logger.warning("Failed to validate credential type %s", credential_type)
        return False


async def _guess_credential_types(name: str) -> list[str] | None:
    """Generate candidates and validate each against the live n8n instance."""
    camel = _normalize_to_camel_case(name)
    if not camel:
        return None
    candidates = _generate_candidates(camel)
    for candidate in candidates:
        if await _validate_credential_type(candidate):
            logger.info("Convention guess matched: %r -> %s", name, candidate)
            return [candidate]
    return None


async def resolve_credential_types(name: str) -> list[str]:
    """Resolve an integration name to n8n credential type(s).

    5-step chain:
    1. Aliases (deterministic, for known edge cases)
    2. Hardcoded NODE_CREDENTIAL_MAP (fast path)
    3. Convention guessing + n8n API validation
    4. LLM fallback (structured output)
    5. Empty list (skip with warning)
    """
    # Defensive: split CSV strings that leaked through normalization
    if "," in name:
        logger.warning(
            "resolve_credential_types received CSV string %r — splitting", name,
        )
        results: list[str] = []
        for part in name.split(","):
            part = part.strip()
            if part:
                results.extend(await resolve_credential_types(part))
        return results

    normalized = name.strip().lower().replace("-", "")

    # Step 1: Alias lookup
    alias_key = INTEGRATION_ALIASES.get(normalized)
    if alias_key and alias_key in NODE_CREDENTIAL_MAP:
        return NODE_CREDENTIAL_MAP[alias_key]

    # Step 2: Hardcoded map lookup
    map_lookup = {k.lower(): k for k in NODE_CREDENTIAL_MAP}
    compact = normalized.replace(" ", "")
    if compact in map_lookup:
        return NODE_CREDENTIAL_MAP[map_lookup[compact]]

    # Check runtime cache (from previous convention guess or LLM resolution)
    if compact in _runtime_cache:
        return _runtime_cache[compact]

    # Step 3: Convention guess
    guessed = await _guess_credential_types(name)
    if guessed:
        _runtime_cache[compact] = guessed
        NODE_CREDENTIAL_MAP[_normalize_to_camel_case(name)] = guessed
        return guessed

    # Step 4: LLM fallback
    llm_result = await llm_resolve(name)
    if llm_result:
        _runtime_cache[compact] = llm_result
        NODE_CREDENTIAL_MAP[_normalize_to_camel_case(name)] = llm_result
        return llm_result

    # Step 5: No match
    logger.warning(
        "Could not resolve credential types for integration %r", name,
    )
    return []
