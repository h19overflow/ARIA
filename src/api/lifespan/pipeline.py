"""FastAPI dependency + lifespan helper for the ARIAPipeline singleton."""
from fastapi import Request

from src.agentic_system.graph import ARIAPipeline

_pipeline: ARIAPipeline | None = None


async def startup() -> None:
    global _pipeline
    _pipeline = ARIAPipeline()


async def shutdown() -> None:
    global _pipeline
    _pipeline = None


def get_pipeline(request: Request) -> ARIAPipeline:  # noqa: ARG001
    if _pipeline is None:
        raise RuntimeError("ARIAPipeline not initialised — lifespan not running")
    return _pipeline
