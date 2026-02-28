# Build Cycle Graph

Takes the `BuildBlueprint` from the completed Conversation (Phase 0) and incrementally builds, deploys, tests, and activates a live n8n workflow using parallel node workers and fan-in assembly.

> **Upstream dependency:** The build cycle requires `committed=true` AND `credentials_committed=true` in the `conversation:{id}` Redis state. Credentials are resolved dynamically by Phase 0's [5-step credential resolver](../shared/credential_resolver.py) before reaching the build cycle.

---

## Workflow

<!-- mermaid-source-file:.mermaid\README_1772311172_163.mmd-->

![Mermaid Diagram](.mermaid\README_diagram_1772311172_163.svg)

**Blue = Agentic (LLM call + tool use)** · **Yellow = Pauses for user input** · **Green = Deterministic / API call**

---

## Node Reference

| Node | Agentic? | Pauses? | What it does |
|---|---|---|---|
| **Node Planner** | Yes (+ `search_n8n_nodes` tool) | No | Calls `discover_installed_node_prefixes()` to get available packages, then reasons over intent, topology, and credentials. Uses the `search_n8n_nodes` tool on-demand to query ChromaDB for node docs before selecting types. Produces a flat `NodePlan` with `NodeSpec` objects and `PlannedEdge` connections. Detects and corrects cycles. MUST ONLY use installed packages — falls back to `httpRequest` or `code` otherwise. |
| **Node Worker** (parallel) | Yes (+ `search_n8n_nodes` tool) | No | Spawned in parallel via Send API. Uses `search_n8n_nodes` tool to look up parameter schemas for its node type, then builds a single n8n node JSON from its `NodeSpec`. Applies credential IDs, generates UUIDs, and calculates canvas position. |
| **Assembler** | Yes | No | Fan-in: collects all `node_build_results`, validates them (short-circuits to debugger if any fail), checks for dangling edges, and merges nodes + connections into final `workflow_json`. |
| **Deploy** | No | No | Creates (POST) or updates (PUT) the workflow in n8n via the REST API. Catches HTTP errors and routes to Debugger instead of crashing. |
| **Test** | No | No | Activates the workflow. Webhook → fire + poll execution. Non-webhook → activation success = pass. |
| **Debugger** | Yes | No | Classifies the error (`schema`, `auth`, `rate_limit`, `logic`, `missing_node`) and applies a targeted fix in one LLM call. Routes `missing_node` to the Node Substituter. |
| **Node Substituter** | Yes | No | LLM-powered recovery for unavailable node types. Replaces missing nodes with `n8n-nodes-base.*` built-in alternatives (typically `httpRequest` or `code`). Escalates to HITL if no substitution is possible. |
| **Activate** | No | No | Permanently activates the workflow, returns the live webhook URL (None for non-webhook). |
| **HITL Escalation** | No | Yes | Fix budget exhausted — generates plain-English explanation, pauses for user: retry / replan / abort. For `missing_node` errors, provides deterministic install instructions instead of LLM-generated explanation. |

---

## RAG Retrieval — Tool-Based (search_n8n_nodes)

Previously, RAG retrieval was a dedicated graph node (`rag_retriever_node`) that pre-fetched all templates into state before planning. This caused two problems:

1. **Context bloat** — all templates were dumped into `ARIAState.node_templates` and carried through every subsequent node
2. **No iterative search** — the planner saw only 12 compressed summaries and couldn't search for alternatives when a node type wasn't installed

Now, RAG retrieval is an on-demand LangChain tool (`search_n8n_nodes`) bound to both the Node Planner and Node Worker agents. The tool wraps `ChromaStore.hybrid_query_n8n_documents()` (BM25 + semantic RRF fusion) and returns up to 5 results per query.

**Tool interface:**
```python
@tool(args_schema=SearchInput)
async def search_n8n_nodes(query: str, doc_type: str | None = "node") -> str:
    """Search the n8n knowledge base for node documentation and parameter templates."""
```

**How agents use it:**
- **Planner:** Searches for each node type before selecting it, verifies it exists in an installed package, searches for alternatives if needed
- **Worker:** Searches for the specific node type it's building to get parameter schemas

**Location:** `src/agentic_system/build_cycle/tools/search_nodes.py`

---

## Agent Internals

### Node Planner

<!-- mermaid-source-file:.mermaid\README_1772311172_164.mmd-->

![Mermaid Diagram](.mermaid\README_diagram_1772311172_164.svg)

**Planning rules:**
- Output a flat list of `NodeSpec` objects (no phases)
- MUST ONLY use node types from installed packages
- Use `search_n8n_nodes` tool before selecting any node type
- Fall back to `n8n-nodes-base.httpRequest` or `n8n-nodes-base.code` when no dedicated node exists
- Include conditional branch hints (IF/Switch)
- Preserve all topology edges
- Ensure no cycles in planned edges

**Output shape:**
```python
NodePlan {
    nodes: [NodeSpec, NodeSpec, ...],       # all nodes to build (parallel)
    edges: [PlannedEdge, PlannedEdge, ...], # all connections
    overall_strategy: "...",                # one-sentence explanation
}

NodeSpec {
    node_name: str,              # display name
    node_type: str,              # n8n type identifier
    parameter_hints: dict,       # planner-supplied overrides
    credential_id: str | None,   # resolved credential UUID
    credential_type: str | None, # credential type name
    position_index: int,         # layout ordering hint
}

PlannedEdge {
    from_node: str,              # source node name
    to_node: str,                # target node name
    branch: str | None,          # conditional branch label (for If/Switch)
}
```

---

### Node Worker (parallel)

<!-- mermaid-source-file:.mermaid\README_1772311172_165.mmd-->

![Mermaid Diagram](.mermaid\README_diagram_1772311172_165.svg)

**Each worker:**
- Receives one `NodeSpec` and credential IDs
- Uses `search_n8n_nodes` tool to look up parameter schemas on-demand
- Calls LLM to generate complete `parameters`
- Wraps parameters into full n8n node JSON
- Returns a `NodeResult` with pass/fail status
- Runs in parallel with all other workers

---

### Assembler (Fan-In)

<!-- mermaid-source-file:.mermaid\README_1772311172_166.mmd-->

![Mermaid Diagram](.mermaid\README_diagram_1772311172_166.svg)

**Validation gate:**
- Checks all `NodeResult` objects for `validation_passed: false`
- Scans `planned_edges` for references to nodes not in `node_build_results`
- Short-circuits to Debugger with `type: "schema"` if any fail
- Otherwise, merges nodes and connections into final workflow JSON

---

### Debugger

<!-- mermaid-source-file:.mermaid\README_1772311172_167.mmd-->

![Mermaid Diagram](.mermaid\README_diagram_1772311172_167.svg)

**Error classification:**
| Signal in error message | `error_type` | Auto-fixed? |
|---|---|---|
| JSON parse errors, missing fields, invalid syntax | `schema` | Yes |
| Wrong values, logic flow, data shape mismatch | `logic` | Yes |
| 401, 403, token expired, unauthorized | `auth` | No — escalate |
| 429, rate limit exceeded | `rate_limit` | No — retry test |
| Unknown node type, unrecognized node, package not installed | `missing_node` | No — route to Node Substituter |

**Fix constraints:** can only change the named node's `parameters`. Cannot add/remove nodes, connections, or touch credential IDs.

---

### HITL Escalation

<!-- mermaid-source-file:.mermaid\README_1772311172_168.mmd-->

![Mermaid Diagram](.mermaid\README_diagram_1772311172_168.svg)

---

### Test Node (trigger-aware)

<!-- mermaid-source-file:.mermaid\README_1772311172_169.mmd-->

![Mermaid Diagram](.mermaid\README_diagram_1772311172_169.svg)

---

## State Flow Summary

```
conversation:{id} (committed + credentials resolved)
    ↓ Build Service      → validate_conversation_for_build(), convert to ARIAState
BuildBlueprint
    ↓ Node Planner       → discover_installed_node_prefixes(), search_n8n_nodes tool,
    ↓                       nodes_to_build[], planned_edges[], available_node_packages[]
    ↓ Fan-Out (Send)     → spawn parallel Node Workers
    ↓ Node Workers       → search_n8n_nodes tool, node_build_results[] (parallel)
    ↓ Assembler          → workflow_json (merged + validated), status="building"
    ↓ Deploy             → n8n_workflow_id
    ↓ Test               → execution_result → "done" | "fixing"
    ↓   (fixing)
    ↓ Debugger           → classified_error, workflow_json (patched), fix_attempts++
    ↓   (missing_node)
    ↓ Node Substituter   → workflow_json (node replaced with built-in), status="building" → Deploy
    ↓   (done)
    ↓ Activate           → webhook_url, status="done"
```

---

## What Streams to the UI

| Event | What the UI sees | Type |
|---|---|---|
| Node Planner fires | `"Strategy: X → N nodes queued: [node], [node]..."` | Per-node update |
| Node Workers fire (parallel) | `"Building NodeA..."`, `"Building NodeB..."` (one per worker) | Per-node update |
| Assembler fires | `"Assembled N nodes into workflow."` | Per-node update |
| Deploy fires | `"Deployed workflow <id>"` | Per-node update |
| Test fires | `"Execution success/error: <exec_id>"` or `"Activation success (non-webhook trigger)"` | Per-node update |
| Debugger fires | `"<type> in '<node>': <message>"` + `"Fix applied: <explanation>"` | Per-node update |
| HITL Escalation fires | interrupt payload with explanation + options | **Interrupt** (graph pauses) |
| Activate fires | `"Workflow live! Webhook: <url>"` or `"Webhook: N/A"` | Per-node update |

> Updates are **per-node**, not token-by-token. Each node fires once when it completes.

---

## Trigger Detection (`nodes/_trigger_utils.py`)

Shared utility used by `test.py`, `activate.py`, and the benchmark runner. Single source of truth.

```python
detect_trigger_type(workflow_json) → "webhook" | "schedule" | "other"
extract_webhook_path(workflow_json) → str   # fallback: "test-webhook"
```

Detection scans `workflow_json.nodes` for known type strings:
- `"webhook"` → type contains `"webhook"` (e.g. `n8n-nodes-base.webhook`)
- `"schedule"` → `n8n-nodes-base.scheduletrigger`, `n8n-nodes-base.cron`, or type contains `"schedule"` / `"cron"`
- `"other"` → anything else

---

## Isolation Test Scripts

```bash
# Run 3 simple fixtures against live n8n (fast, ~3 min)
python scripts/_run_simple_benchmark.py

# Run full 9-fixture benchmark (~30 min)
python scripts/benchmark_build_cycle.py

# Test Deploy → Test → Debug loop against an existing workflow ID
python scripts/test_build_cycle_real.py
```
