"""Load YAML configs and instantiate the corresponding retriever."""
from __future__ import annotations

from pathlib import Path

import yaml

from benchmarks.adapters.base import BaseRetriever
from benchmarks.adapters.chroma_adapter import (
    ChromaHybridRetriever,
    ChromaSemanticRetriever,
)
from benchmarks.adapters.chunked_adapter import ChunkedRetriever
from benchmarks.adapters.huggingface_adapter import HuggingFaceRetriever
from benchmarks.adapters.rerank_adapter import RerankRetriever

CONFIGS_DIR = Path(__file__).parent / "configs"

_ADAPTER_BUILDERS = {
    "chroma_hybrid": lambda p: ChromaHybridRetriever(alpha=p.get("alpha")),
    "chroma_semantic": lambda p: ChromaSemanticRetriever(),
    "huggingface": lambda p: HuggingFaceRetriever(
        model_name=p["model_name"],
        search_mode=p.get("search_mode", "hybrid"),
    ),
    "chunked": lambda p: ChunkedRetriever(
        chunk_size=p.get("chunk_size", 512),
        chunk_overlap=p.get("chunk_overlap", 64),
        strategy=p.get("strategy", "fixed"),
    ),
}


def load_config(path: Path) -> dict:
    """Parse a single YAML config file."""
    return yaml.safe_load(path.read_text())


def build_retriever(config: dict) -> BaseRetriever:
    """Instantiate a retriever from a parsed config dict."""
    adapter = config["adapter"]
    params = config.get("params") or {}

    if adapter == "rerank":
        inner_name = params["inner_adapter"]
        inner = _ADAPTER_BUILDERS[inner_name]({})
        return RerankRetriever(inner, reranker=params["reranker"])

    builder = _ADAPTER_BUILDERS.get(adapter)
    if builder is None:
        raise ValueError(f"Unknown adapter: {adapter}")
    return builder(params)


def load_all_configs() -> list[dict]:
    """Load all YAML configs from the configs directory."""
    configs = []
    for path in sorted(CONFIGS_DIR.glob("*.yaml")):
        configs.append(load_config(path))
    return configs
