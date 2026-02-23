"""
FastAPI dependency + lifespan helper for the ChromaStore singleton.
"""

from fastapi import Request

from src.boundary.chroma.store import ChromaStore

_store: ChromaStore | None = None


async def startup() -> None:
    global _store
    _store = ChromaStore()
    await _store.connect()


async def shutdown() -> None:
    global _store
    if _store is not None:
        await _store.disconnect()
        _store = None


def get_chroma(request: Request) -> ChromaStore:  # noqa: ARG001
    """FastAPI dependency — injects the shared ChromaStore instance."""
    if _store is None:
        raise RuntimeError("ChromaStore not initialised — lifespan not running")
    return _store
