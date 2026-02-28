"""
Scrapes n8n node documentation and workflow templates.

Node docs  → httpx + BeautifulSoup (fully static HTML)
Workflows  → api.n8n.io/api/templates REST API (fast JSON, no browser)
"""

import asyncio
from urllib.parse import urljoin, urldefrag

import httpx
from bs4 import BeautifulSoup

from src.boundary.scraper._internals.normalizer import N8nDocument, normalize_node, normalize_workflow_template

DOCS_BASE = "https://docs.n8n.io"
NODE_INDEX_URL = f"{DOCS_BASE}/integrations/builtin/app-nodes/"
TEMPLATES_API = "https://api.n8n.io/api/templates"
TEMPLATES_PAGE_URL = "https://n8n.io/workflows/{id}"

# Concurrency limits
NODE_CONCURRENCY = 5
WORKFLOW_CONCURRENCY = 20  # pure HTTP — can go much higher


# ---------------------------------------------------------------------------
# Public entry points
# ---------------------------------------------------------------------------

async def scrape_all_nodes() -> list[N8nDocument]:
    """Fetch every n8n node page and return normalised documents."""
    urls = await _discover_node_urls()
    return await _fetch_nodes_concurrent(urls)


async def scrape_workflow_templates(limit: int = 1000) -> list[N8nDocument]:
    """
    Fetch workflow templates from the n8n templates REST API.
    Returns up to `limit` templates as normalised N8nDocuments.
    Uses pure httpx — no browser required.
    """
    ids = await _discover_template_ids(limit=limit)
    return await _fetch_templates_concurrent(ids)


# ---------------------------------------------------------------------------
# Node scraping (static HTML)
# ---------------------------------------------------------------------------

async def _discover_node_urls() -> list[str]:
    """Parse the node index page and return all individual node page URLs."""
    async with httpx.AsyncClient(follow_redirects=True, timeout=30) as client:
        response = await client.get(NODE_INDEX_URL)
        response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    seen: set[str] = set()
    urls: list[str] = []

    for anchor in soup.find_all("a", href=True):
        href: str = anchor["href"]
        if "n8n-nodes-base." not in href and "n8n-nodes-langchain." not in href:
            continue
        full_url = href if href.startswith("http") else urljoin(NODE_INDEX_URL, href)
        clean, _ = urldefrag(full_url)
        if clean not in seen:
            seen.add(clean)
            urls.append(clean)

    return urls


async def _fetch_nodes_concurrent(urls: list[str]) -> list[N8nDocument]:
    semaphore = asyncio.Semaphore(NODE_CONCURRENCY)
    async with httpx.AsyncClient(follow_redirects=True, timeout=30) as client:
        tasks = [_fetch_one_node(client, semaphore, url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
    return [r for r in results if isinstance(r, N8nDocument)]


async def _fetch_one_node(
    client: httpx.AsyncClient,
    semaphore: asyncio.Semaphore,
    url: str,
) -> N8nDocument | None:
    async with semaphore:
        try:
            response = await client.get(url)
            response.raise_for_status()
            return _parse_node_page(response.text, url)
        except Exception:
            return None


def _parse_node_page(html: str, url: str) -> N8nDocument:
    soup = BeautifulSoup(html, "html.parser")
    name = _extract_text(soup, "h1") or url.rstrip("/").split(".")[-1]
    description = _extract_text(soup, "p") or ""
    operations = _extract_operations(soup)
    parameters = _extract_parameters(soup)
    node_type = url.rstrip("/").split("/")[-1]
    return normalize_node({
        "name": name,
        "node_type": node_type,
        "description": description,
        "operations": operations,
        "parameters": parameters,
        "type_version": "1",
        "url": url,
    })


def _extract_text(soup: BeautifulSoup, tag: str) -> str:
    el = soup.find(tag)
    return el.get_text(strip=True) if el else ""


def _extract_operations(soup: BeautifulSoup) -> list[str]:
    for heading in soup.find_all(["h2", "h3"]):
        if "operation" in heading.get_text(strip=True).lower():
            sibling = heading.find_next_sibling()
            if sibling and sibling.name in ("ul", "table"):
                return [li.get_text(strip=True) for li in sibling.find_all("li")]
    return []


def _extract_parameters(soup: BeautifulSoup) -> list[str]:
    for heading in soup.find_all(["h2", "h3"]):
        if "parameter" in heading.get_text(strip=True).lower():
            sibling = heading.find_next_sibling()
            if sibling and sibling.name in ("ul", "table"):
                return [li.get_text(strip=True) for li in sibling.find_all("li")]
    return []


# ---------------------------------------------------------------------------
# Workflow template scraping (REST API — no browser)
# ---------------------------------------------------------------------------

async def _discover_template_ids(limit: int) -> list[int]:
    """Page through the templates search API and collect workflow IDs."""
    ids: list[int] = []
    page = 1
    page_size = 50

    async with httpx.AsyncClient(timeout=30) as client:
        while len(ids) < limit:
            resp = await client.get(
                f"{TEMPLATES_API}/search",
                params={"page": page, "rows": page_size},
            )
            resp.raise_for_status()
            data = resp.json()
            workflows = data.get("workflows", [])
            if not workflows:
                break
            ids.extend(w["id"] for w in workflows)
            if len(ids) >= data.get("totalWorkflows", 0):
                break
            page += 1

    return ids[:limit]


async def _fetch_templates_concurrent(ids: list[int]) -> list[N8nDocument]:
    semaphore = asyncio.Semaphore(WORKFLOW_CONCURRENCY)
    async with httpx.AsyncClient(timeout=30) as client:
        tasks = [_fetch_one_template(client, semaphore, wf_id) for wf_id in ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)
    return [r for r in results if isinstance(r, N8nDocument)]


async def _fetch_one_template(
    client: httpx.AsyncClient,
    semaphore: asyncio.Semaphore,
    wf_id: int,
) -> N8nDocument | None:
    async with semaphore:
        try:
            resp = await client.get(f"{TEMPLATES_API}/workflows/{wf_id}")
            resp.raise_for_status()
            data = resp.json().get("workflow", {})
            nodes_used = list({
                n["type"] for n in data.get("nodes", [])
                if n.get("type")
            })
            return normalize_workflow_template({
                "id": str(wf_id),
                "name": data.get("name", ""),
                "description": data.get("description", ""),
                "nodes_used": nodes_used,
                "url": TEMPLATES_PAGE_URL.format(id=wf_id),
                "nodes": data.get("nodes", []),
                "connections": data.get("connections", {}),
            })
        except Exception:
            return None
