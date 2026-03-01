"""
Generate golden dataset from live ChromaDB.
1. Connect to ChromaDB, extract all unique node_type values
2. Use Gemini to generate categorized queries per node
3. Write golden_dataset.json
"""
import asyncio
import json
from pathlib import Path

from langchain_google_genai import ChatGoogleGenerativeAI

from src.api.settings import settings
from src.boundary.chroma.store import ChromaStore
from benchmarks.schema import (
    GoldenQuery, GoldenDataset, QueryCategory, Difficulty,
)

BENCHMARKS_DIR = Path(__file__).parent
OUTPUT_PATH = BENCHMARKS_DIR / "golden_dataset.json"

GENERATION_PROMPT = """You are generating test queries for an n8n node search system.

Given this n8n node: {node_name} (type: {node_type})
Description: {description}

Generate exactly 5 search queries a user might type to find this node:

1. natural_language: A natural sentence describing what they want to do (e.g., "send an email notification")
2. exact_lookup: The node name or type ID directly (e.g., "Gmail node")
3. partial_description: Describe the functionality without naming the node (e.g., "the node that sends emails")
4. misspelled: A realistic typo of the node name (e.g., "gogle sheets")
5. ambiguous: A vague query where this node is one valid answer (e.g., "message service")

Return JSON array with objects: {{"query": "...", "category": "...", "difficulty": "easy|medium|hard"}}
"""

MULTI_NODE_PROMPT = """Generate 3 multi-node search queries combining these n8n nodes:
Nodes: {node_names}

Each query should describe a workflow that needs ALL listed nodes.
Return JSON array: [{{"query": "...", "expected_nodes": [...], "difficulty": "medium|hard"}}]
"""


async def extract_node_metadata(store: ChromaStore) -> list[dict]:
    """Fetch all node documents and extract unique node metadata."""
    raw = store._n8n_store.get(include=["metadatas"])
    seen = set()
    nodes = []
    for meta in raw["metadatas"]:
        if meta.get("doc_type") != "node":
            continue
        node_type = meta.get("node_type", "")
        if node_type in seen:
            continue
        seen.add(node_type)
        nodes.append({
            "name": meta.get("name", ""),
            "node_type": node_type,
            "description": meta.get("description", ""),
        })
    return nodes


def _extract_text(content: str | list) -> str:
    """Extract plain text from LLM response content (may be str or list of blocks)."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(block.get("text", "") for block in content if isinstance(block, dict))
    return str(content)


def _parse_json_response(content: str | list) -> list[dict]:
    """Extract and parse JSON array from LLM response, stripping markdown fences."""
    text = _extract_text(content).strip()
    text = text.strip("`")
    if text.startswith("json"):
        text = text[4:]
    text = text.strip()
    return json.loads(text)


async def generate_queries_for_node(
    llm: ChatGoogleGenerativeAI,
    node: dict,
) -> list[GoldenQuery]:
    """Generate categorized queries for a single node via LLM."""
    prompt = GENERATION_PROMPT.format(
        node_name=node["name"],
        node_type=node["node_type"],
        description=node["description"],
    )
    response = await llm.ainvoke(prompt)
    raw = _parse_json_response(response.content)

    queries = []
    for i, item in enumerate(raw):
        category = QueryCategory(item["category"])
        queries.append(GoldenQuery(
            id=f"{category.value}_{node['node_type']}_{i}",
            category=category,
            query=item["query"],
            expected_nodes=[node["node_type"]],
            difficulty=Difficulty(item.get("difficulty", "medium")),
        ))
    return queries


async def generate_multi_node_queries(
    llm: ChatGoogleGenerativeAI,
    node_pairs: list[list[dict]],
) -> list[GoldenQuery]:
    """Generate multi-node queries from common integration pairs."""
    queries = []
    for pair in node_pairs:
        names = [n["name"] for n in pair]
        types = [n["node_type"] for n in pair]
        prompt = MULTI_NODE_PROMPT.format(node_names=", ".join(names))
        try:
            response = await llm.ainvoke(prompt)
            raw = _parse_json_response(response.content)
            for i, item in enumerate(raw):
                queries.append(GoldenQuery(
                    id=f"multi_{'-'.join(types)}_{i}",
                    category=QueryCategory.MULTI_NODE,
                    query=item["query"],
                    expected_nodes=types,
                    difficulty=Difficulty(item.get("difficulty", "medium")),
                ))
        except (json.JSONDecodeError, KeyError, ValueError) as exc:
            print(f"  SKIP multi-node {names}: {exc}")
    return queries


def save_dataset(dataset: GoldenDataset) -> Path:
    """Serialize golden dataset to JSON."""
    data = {
        "version": dataset.version,
        "queries": [
            {
                "id": q.id,
                "category": q.category.value,
                "query": q.query,
                "expected_nodes": q.expected_nodes,
                "expected_doc_type": q.expected_doc_type,
                "difficulty": q.difficulty.value,
            }
            for q in dataset.queries
        ],
    }
    OUTPUT_PATH.write_text(json.dumps(data, indent=2))
    return OUTPUT_PATH


async def main() -> None:
    store = ChromaStore()
    await store.connect()
    llm = ChatGoogleGenerativeAI(
        model=settings.gemini_model,
        google_api_key=settings.google_api_key,
    )

    all_nodes = await extract_node_metadata(store)
    nodes = all_nodes[:50]
    print(f"Found {len(all_nodes)} unique nodes, using first {len(nodes)}")

    all_queries: list[GoldenQuery] = []

    # Single-node queries (5 per node)
    failed = 0
    for i, node in enumerate(nodes):
        try:
            queries = await generate_queries_for_node(llm, node)
            all_queries.extend(queries)
            print(f"  [{i+1}/{len(nodes)}] Generated {len(queries)} queries for {node['name']}")
        except (json.JSONDecodeError, KeyError, ValueError) as exc:
            failed += 1
            print(f"  [{i+1}/{len(nodes)}] SKIP {node['name']}: {exc}")
    if failed:
        print(f"  Skipped {failed}/{len(nodes)} nodes due to LLM parse errors")

    # Multi-node queries from common pairs
    common_pairs = _build_common_pairs(nodes)
    multi = await generate_multi_node_queries(llm, common_pairs)
    all_queries.extend(multi)
    print(f"  Generated {len(multi)} multi-node queries")

    # Add workflow template queries
    template_queries = _build_template_queries()
    all_queries.extend(template_queries)

    dataset = GoldenDataset(queries=all_queries)
    path = save_dataset(dataset)
    print(f"Saved {len(all_queries)} queries to {path}")
    await store.disconnect()


def _build_common_pairs(nodes: list[dict]) -> list[list[dict]]:
    """Select common integration pairs for multi-node queries."""
    by_type = {n["node_type"]: n for n in nodes}
    pairs = [
        ["n8n-nodes-base.webhook", "n8n-nodes-base.slack"],
        ["n8n-nodes-base.gmail", "n8n-nodes-base.telegram"],
        ["n8n-nodes-base.webhook", "n8n-nodes-base.googleSheets"],
        ["n8n-nodes-base.httpRequest", "n8n-nodes-base.slack"],
        ["n8n-nodes-base.webhook", "n8n-nodes-base.gmail", "n8n-nodes-base.slack"],
    ]
    result = []
    for pair in pairs:
        resolved = [by_type[t] for t in pair if t in by_type]
        if len(resolved) == len(pair):
            result.append(resolved)
    return result


def _build_template_queries() -> list[GoldenQuery]:
    """Static workflow template queries."""
    return [
        GoldenQuery(
            id="wf_001",
            category=QueryCategory.WORKFLOW_TEMPLATE,
            query="daily email report workflow",
            expected_nodes=[],
            expected_doc_type="workflow_template",
            difficulty=Difficulty.MEDIUM,
        ),
        GoldenQuery(
            id="wf_002",
            category=QueryCategory.WORKFLOW_TEMPLATE,
            query="slack notification when new row added to google sheets",
            expected_nodes=[],
            expected_doc_type="workflow_template",
            difficulty=Difficulty.MEDIUM,
        ),
    ]


if __name__ == "__main__":
    asyncio.run(main())
