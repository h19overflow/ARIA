"""ARIA FastAPI application entry point."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logging.getLogger("aria").setLevel(logging.DEBUG)

from src.api.lifespan import chroma as chroma_lifespan
from src.api.lifespan import redis as redis_lifespan
from src.api.routers import ingestion, workflows, jobs


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ARG001
    await chroma_lifespan.startup()
    await redis_lifespan.startup()
    yield
    await redis_lifespan.shutdown()
    await chroma_lifespan.shutdown()


app = FastAPI(
    title="ARIA",
    description="Agentic Real-time Intelligence Architect — n8n workflow automation via LLM.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ingestion.router)
app.include_router(workflows.router)
app.include_router(jobs.router)
