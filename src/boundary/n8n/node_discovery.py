"""Discover installed n8n node type prefixes via introspection or config fallback."""
from __future__ import annotations

import logging

import httpx

from src.api.settings import settings

logger = logging.getLogger(__name__)

# Always-available built-in package
_BUILTIN_PACKAGE = "n8n-nodes-base"


async def discover_installed_node_prefixes() -> set[str]:
    """Return set of installed node type prefixes (e.g. {'n8n-nodes-base', '@n8n/n8n-nodes-langchain'}).

    Strategy:
    1. Try n8n's internal /types/nodes.json endpoint (undocumented, self-hosted only).
    2. Fall back to settings.n8n_installed_packages.
    3. Always include 'n8n-nodes-base'.
    """
    prefixes = await _try_introspection()
    if prefixes is None:
        prefixes = _load_from_config()
    prefixes.add(_BUILTIN_PACKAGE)
    logger.info("[NodeDiscovery] Resolved %d installed package(s): %s", len(prefixes), prefixes)
    return prefixes


async def _try_introspection() -> set[str] | None:
    """Attempt to fetch node types from n8n and extract unique prefixes."""
    base_url = settings.n8n_base_url.rstrip("/")
    headers = {"X-N8N-API-KEY": settings.n8n_api_key}
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{base_url}/types/nodes.json", headers=headers)
            if resp.status_code != 200:
                logger.debug("[NodeDiscovery] /types/nodes.json returned %d, falling back to config", resp.status_code)
                return None
            nodes = resp.json()
            return _extract_prefixes_from_node_list(nodes)
    except (httpx.HTTPError, ValueError, KeyError) as exc:
        logger.debug("[NodeDiscovery] Introspection failed: %s", exc)
        return None


def _extract_prefixes_from_node_list(nodes: list | dict) -> set[str]:
    """Extract package prefixes from n8n node type identifiers.

    Node types look like 'n8n-nodes-base.gmail' or '@n8n/n8n-nodes-langchain.lmChatGoogleGemini'.
    The prefix is everything before the last dot-segment.
    """
    prefixes: set[str] = set()
    items = nodes if isinstance(nodes, list) else []
    for item in items:
        name = item.get("name", "") if isinstance(item, dict) else str(item)
        prefix = _extract_prefix(name)
        if prefix:
            prefixes.add(prefix)
    return prefixes


def _extract_prefix(node_type: str) -> str:
    """Extract package prefix from a full node type string.

    'n8n-nodes-base.gmail' -> 'n8n-nodes-base'
    '@n8n/n8n-nodes-langchain.lmChatGoogleGemini' -> '@n8n/n8n-nodes-langchain'
    """
    if not node_type or "." not in node_type:
        return ""
    return node_type.rsplit(".", 1)[0]


def _load_from_config() -> set[str]:
    """Load installed packages from settings."""
    logger.info("[NodeDiscovery] Using config fallback: %s", settings.n8n_installed_packages)
    return set(settings.n8n_installed_packages)
