"""
Ingestion use cases.
Triggers scraping/parsing and upserts results into ChromaDB.
"""

from src.boundary.chroma.store import ChromaStore
from src.boundary.scraper.n8n_scraper import scrape_all_nodes, scrape_workflow_templates
from src.boundary.scraper.api_parser import parse_api_spec


async def ingest_n8n_nodes(store: ChromaStore) -> dict:
    """Scrape all n8n node docs and upsert into ChromaDB."""
    documents = await scrape_all_nodes()
    await store.upsert_n8n_documents(documents)
    return {"type": "nodes", "ingested": len(documents)}


async def ingest_n8n_workflow_templates(
    store: ChromaStore,
    limit: int = 200,
) -> dict:
    """Scrape n8n workflow templates (via Playwright) and upsert into ChromaDB."""
    documents = await scrape_workflow_templates(limit=limit)
    await store.upsert_n8n_documents(documents)
    return {"type": "workflow_templates", "ingested": len(documents)}


async def ingest_api_spec(
    store: ChromaStore,
    spec: dict,
    source_name: str,
) -> dict:
    """Parse an OpenAPI / Swagger / Postman spec and upsert endpoints into ChromaDB."""
    endpoints = parse_api_spec(spec, source_name)
    await store.upsert_api_endpoints(endpoints)
    return {"type": "api_spec", "source": source_name, "ingested": len(endpoints)}
