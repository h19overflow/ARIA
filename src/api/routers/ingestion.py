from fastapi import APIRouter, Depends

from src.api.lifespan.chroma import get_chroma
from src.api.schemas import (
    IngestN8nResponse,
    IngestApiSpecRequest,
    IngestApiSpecResponse,
)
from src.boundary.chroma.store import ChromaStore
from src.services.rag import ingestion

router = APIRouter(prefix="/ingest", tags=["ingestion"])


@router.post("/n8n/nodes", response_model=IngestN8nResponse)
async def ingest_n8n_nodes(
    store: ChromaStore = Depends(get_chroma),
) -> IngestN8nResponse:
    result = await ingestion.ingest_n8n_nodes(store)
    return IngestN8nResponse(**result)


@router.post("/n8n/workflows", response_model=IngestN8nResponse)
async def ingest_n8n_workflow_templates(
    limit: int = 200,
    store: ChromaStore = Depends(get_chroma),
) -> IngestN8nResponse:
    result = await ingestion.ingest_n8n_workflow_templates(store, limit=limit)
    return IngestN8nResponse(**result)


@router.post("/api-spec", response_model=IngestApiSpecResponse)
async def ingest_api_spec(
    body: IngestApiSpecRequest,
    store: ChromaStore = Depends(get_chroma),
) -> IngestApiSpecResponse:
    result = await ingestion.ingest_api_spec(store, body.spec, body.source_name)
    return IngestApiSpecResponse(**result)
