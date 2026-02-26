"""ARIA FastAPI application entry point."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.lifespan import chroma as chroma_lifespan
from src.api.lifespan import conversation as conversation_lifespan
from src.api.lifespan import n8n as n8n_lifespan
from src.api.lifespan import pipeline as pipeline_lifespan
from src.api.lifespan import preflight as preflight_lifespan
from src.api.lifespan import redis as redis_lifespan
from src.api.routers import ingestion, preflight, build, jobs, conversation, credentials

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logging.getLogger("aria").setLevel(logging.DEBUG)



@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ARG001
    await chroma_lifespan.startup()
    await redis_lifespan.startup()
    await n8n_lifespan.startup()
    await conversation_lifespan.startup()
    await preflight_lifespan.startup()
    await pipeline_lifespan.startup()
    yield
    await pipeline_lifespan.shutdown()
    await preflight_lifespan.shutdown()
    await n8n_lifespan.shutdown()
    await redis_lifespan.shutdown()
    await chroma_lifespan.shutdown()
    await conversation_lifespan.shutdown()


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
app.include_router(conversation.router)
app.include_router(preflight.router)
app.include_router(build.router)
app.include_router(jobs.router)
app.include_router(credentials.router)
