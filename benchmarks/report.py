"""
Generate comparison report from benchmark results.
Reads all JSON files from benchmarks/results/, generates markdown table.
"""
from __future__ import annotations

import json
from pathlib import Path

RESULTS_DIR = Path(__file__).parent / "results"
REPORT_PATH = Path(__file__).parent / "REPORT.md"

METRIC_KEYS = [
    "recall@3", "recall@5", "recall@10",
    "precision@3", "precision@5",
    "mrr", "hit_rate@5",
    "latency_ms",
]


def load_all_results() -> list[dict]:
    """Load all benchmark result files."""
    results = []
    for path in sorted(RESULTS_DIR.glob("*.json")):
        data = json.loads(path.read_text())
        results.append(data)
    return results


def build_comparison_table(results: list[dict]) -> str:
    """Build markdown table comparing all retrievers."""
    if not results:
        return "No results found."

    header = "| Retriever | " + " | ".join(METRIC_KEYS) + " |"
    separator = "|---|" + "|".join(["---"] * len(METRIC_KEYS)) + "|"

    rows = []
    for r in results:
        overall = r.get("overall", {})
        values = [str(overall.get(k, "—")) for k in METRIC_KEYS]
        rows.append(f"| {r['retriever']} | " + " | ".join(values) + " |")

    return "\n".join([header, separator] + rows)


def build_category_breakdown(results: list[dict]) -> str:
    """Build per-category metric breakdown for each retriever."""
    sections = []
    for r in results:
        name = r["retriever"]
        cats = r.get("by_category", {})
        lines = [f"### {name}", ""]
        for cat, data in cats.items():
            metrics = data.get("metrics", {})
            line = f"- **{cat}** (n={data['count']}): "
            line += ", ".join(f"{k}={v}" for k, v in metrics.items() if k in METRIC_KEYS)
            lines.append(line)
        sections.append("\n".join(lines))
    return "\n\n".join(sections)


def find_winners(results: list[dict]) -> str:
    """Identify best retriever per metric."""
    if not results:
        return ""

    lines = ["## Winners", ""]
    for metric in METRIC_KEYS:
        best_name = ""
        best_val = -1 if metric != "latency_ms" else float("inf")
        for r in results:
            val = r.get("overall", {}).get(metric, None)
            if val is None:
                continue
            if metric == "latency_ms":
                if val < best_val:
                    best_val = val
                    best_name = r["retriever"]
            elif val > best_val:
                best_val = val
                best_name = r["retriever"]
        lines.append(f"- **{metric}**: {best_name} ({best_val})")
    return "\n".join(lines)


def generate_report() -> Path:
    """Generate full markdown report."""
    results = load_all_results()
    sections = [
        "# RAG Benchmark Report",
        "",
        f"**Variants tested:** {len(results)}",
        f"**Queries per variant:** {results[0]['total_queries'] if results else 0}",
        "",
        "## Overall Comparison",
        "",
        build_comparison_table(results),
        "",
        find_winners(results),
        "",
        "## Per-Category Breakdown",
        "",
        build_category_breakdown(results),
    ]
    report = "\n".join(sections)
    REPORT_PATH.write_text(report)
    return REPORT_PATH


if __name__ == "__main__":
    path = generate_report()
    print(f"Report saved to {path}")
