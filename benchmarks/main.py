"""
CLI entrypoint for the RAG benchmark system.

Usage:
  python -m benchmarks.main generate       # Generate golden dataset
  python -m benchmarks.main run --all      # Run all configs
  python -m benchmarks.main run baseline   # Run single config
  python -m benchmarks.main report         # Generate comparison report
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

from benchmarks.config_loader import CONFIGS_DIR, load_config, build_retriever
from benchmarks.runner import run_benchmark, save_results
from benchmarks.schema import GoldenDataset, GoldenQuery, QueryCategory, Difficulty

GOLDEN_PATH = Path(__file__).parent / "golden_dataset.json"


def load_golden_dataset() -> GoldenDataset:
    """Load golden dataset from JSON."""
    raw = json.loads(GOLDEN_PATH.read_text())
    queries = [
        GoldenQuery(
            id=q["id"],
            category=QueryCategory(q["category"]),
            query=q["query"],
            expected_nodes=q["expected_nodes"],
            expected_doc_type=q.get("expected_doc_type", "node"),
            difficulty=Difficulty(q.get("difficulty", "medium")),
        )
        for q in raw["queries"]
    ]
    return GoldenDataset(version=raw["version"], queries=queries)


async def run_single(config_name: str) -> None:
    """Run benchmark for a single config."""
    config_path = CONFIGS_DIR / f"{config_name}.yaml"
    if not config_path.exists():
        print(f"Config not found: {config_path}")
        return

    config = load_config(config_path)
    retriever = build_retriever(config)
    dataset = load_golden_dataset()

    print(f"Running benchmark: {config['name']} ({len(dataset.queries)} queries)")
    results = await run_benchmark(retriever, dataset)
    path = save_results(results)
    print(f"Results saved to {path}")
    _print_summary(results)


async def run_all() -> None:
    """Run all configs sequentially."""
    dataset = load_golden_dataset()
    for config_path in sorted(CONFIGS_DIR.glob("*.yaml")):
        config = load_config(config_path)
        retriever = build_retriever(config)
        print(f"\n{'='*60}")
        print(f"Running: {config['name']} ({len(dataset.queries)} queries)")
        print(f"{'='*60}")
        results = await run_benchmark(retriever, dataset)
        path = save_results(results)
        print(f"Saved to {path}")
        _print_summary(results)


def _print_summary(results: dict) -> None:
    """Print a quick summary of overall metrics."""
    overall = results.get("overall", {})
    print(f"\n  Retriever: {results['retriever']}")
    for key in ["recall@5", "precision@5", "mrr", "hit_rate@5", "latency_ms"]:
        val = overall.get(key, "—")
        print(f"  {key}: {val}")


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        return

    command = sys.argv[1]

    if command == "generate":
        from benchmarks.generate_golden_dataset import main as gen_main
        asyncio.run(gen_main())
    elif command == "run":
        if len(sys.argv) > 2 and sys.argv[2] == "--all":
            asyncio.run(run_all())
        elif len(sys.argv) > 2:
            asyncio.run(run_single(sys.argv[2]))
        else:
            print("Usage: run --all | run <config_name>")
    elif command == "report":
        from benchmarks.report import generate_report
        path = generate_report()
        print(f"Report saved to {path}")
    else:
        print(f"Unknown command: {command}")
        print(__doc__)


if __name__ == "__main__":
    main()
