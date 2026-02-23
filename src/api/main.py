"""
ARIA FastAPI application entry point.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.api.lifespan import chroma as chroma_lifespan
from src.api.routers import ingestion


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ARG001
    await chroma_lifespan.startup()
    yield
    await chroma_lifespan.shutdown()


app = FastAPI(
    title="ARIA",
    description="Agentic Real-time Intelligence Architect — n8n workflow automation via LLM.",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(ingestion.router)
