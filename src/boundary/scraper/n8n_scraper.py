"""
Scrapes n8n node documentation and workflow templates.

Node docs  → httpx + BeautifulSoup (fully static HTML)
Workflows  → sitemap URL discovery + Playwright (Vue/Nuxt SPA)
"""

import asyncio
import xml.etree.ElementTree as ET

import httpx
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

from src.boundary.scraper._internals.normalizer import N8nDocument, normalize_node, normalize_workflow_template

DOCS_BASE = "https://docs.n8n.io"
NODE_INDEX_URL = f"{DOCS_BASE}/integrations/builtin/app-nodes/"
WORKFLOW_SITEMAP_URL = "https://n8n.io/sitemap-workflows.xml"

# Concurrency limits to avoid hammering the servers
NODE_CONCURRENCY = 5
WORKFLOW_CONCURRENCY = 3


# ---------------------------------------------------------------------------
# Public entry points
# ---------------------------------------------------------------------------

async def scrape_all_nodes() -> list[N8nDocument]:
    """Fetch every n8n node page and return normalised documents."""
    urls = await _discover_node_urls()
    return await _fetch_nodes_concurrent(urls)


async def scrape_workflow_templates(limit: int = 200) -> list[N8nDocument]:
    """
    Discover workflow template URLs from the sitemap, then render each page
    via Playwright to extract the workflow JSON and metadata.
    """
    urls = await _discover_workflow_urls(limit=limit)
    return await _fetch_workflows_concurrent(urls)


# ---------------------------------------------------------------------------
# Node scraping (static HTML)
# ---------------------------------------------------------------------------

async def _discover_node_urls() -> list[str]:
    """Parse the node index page and return all individual node page URLs."""
    async with httpx.AsyncClient(follow_redirects=True, timeout=30) as client:
        response = await client.get(NODE_INDEX_URL)
        response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    urls: list[str] = []

    for anchor in soup.find_all("a", href=True):
        href: str = anchor["href"]
        if "n8n-nodes-base." in href or "n8n-nodes-langchain." in href:
            full_url = href if href.startswith("http") else f"{DOCS_BASE}{href}"
            if full_url not in urls:
                urls.append(full_url)

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

    # Operations are usually listed in the first <table> or <ul> after an "Operations" heading
    operations = _extract_operations(soup)
    parameters = _extract_parameters(soup)

    # node_type derived from URL: .../n8n-nodes-base.slack/ → n8n-nodes-base.slack
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
# Workflow template scraping (Playwright)
# ---------------------------------------------------------------------------

async def _discover_workflow_urls(limit: int) -> list[str]:
    """Parse the n8n workflow sitemap and return up to `limit` URLs."""
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(WORKFLOW_SITEMAP_URL)
        response.raise_for_status()

    root = ET.fromstring(response.text)
    ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    urls = [loc.text for loc in root.findall("sm:url/sm:loc", ns) if loc.text]
    return urls[:limit]


async def _fetch_workflows_concurrent(urls: list[str]) -> list[N8nDocument]:
    semaphore = asyncio.Semaphore(WORKFLOW_CONCURRENCY)
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        tasks = [_fetch_one_workflow(browser, semaphore, url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        await browser.close()

    return [r for r in results if isinstance(r, N8nDocument)]


async def _fetch_one_workflow(browser, semaphore, url: str) -> N8nDocument | None:
    async with semaphore:
        page = await browser.new_page()
        try:
            captured: dict = {}

            async def handle_response(response):
                if "workflow" in response.url and response.status == 200:
                    try:
                        captured["data"] = await response.json()
                    except Exception:
                        pass

            page.on("response", handle_response)
            await page.goto(url, wait_until="networkidle", timeout=30000)

            # Fallback: parse visible page text if no XHR captured
            name = await page.title()
            description = ""
            desc_el = await page.query_selector('meta[name="description"]')
            if desc_el:
                description = await desc_el.get_attribute("content") or ""

            nodes_used: list[str] = []
            workflow_id = url.rstrip("/").split("/")[-1].split("-")[0]

            if "data" in captured:
                data = captured["data"]
                name = data.get("name", name)
                description = data.get("description", description)
                nodes_used = [
                    n.get("type", "") for n in data.get("nodes", []) if n.get("type")
                ]

            return normalize_workflow_template({
                "id": workflow_id,
                "name": name,
                "description": description,
                "nodes_used": nodes_used,
                "url": url,
            })
        except Exception:
            return None
        finally:
            await page.close()
