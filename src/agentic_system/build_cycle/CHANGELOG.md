# Build Cycle Changelog

## 2026-03-02 — Build Cycle Quality Fix + Node Worker Empty Params Fix

### Bug Fixes

**Debugger serialization crash** (`nodes/debugger.py`, `nodes/_debugger_fix.py`)
- Converted `DebuggerOutput` Pydantic model to plain dict via `.model_dump()` before passing to msgpack-serialized state
- All `_debugger_fix.py` functions now use dict access instead of Pydantic attribute access
- Root cause: LangGraph state serialization (msgpack) can't handle Pydantic objects

**Node worker empty parameters** (`nodes/node_worker.py`, `nodes/_node_worker_helpers.py`)
- Removed `schema=WorkerOutput` (structured output / `response_format`) from the BaseAgent
- Gemini's structured output mode caused it to return `{"parameters": {}}` even when search results contained correct parameter docs
- Without structured output, Gemini correctly populates parameters from search + prompt hints
- Added `extract_parameters_from_response()` to parse JSON from text response with fallback to `parameter_hints`
- Root cause: Gemini `response_format` constraint suppresses tool result reasoning

**Node worker parameter validation** (`nodes/node_worker.py`, `nodes/_node_worker_helpers.py`)
- Added `_validate_node_output()` — catches empty params and missing webhook `path` before assembly
- `_failure_result()` now accepts `list[str]` in addition to `Exception`

**Assembler connection validation** (`nodes/assembler.py`, `prompts/assembler.py`)
- Added `_validate_connections()` — checks every planned edge has a corresponding connection
- Catches empty connections dict when 2+ nodes exist
- Strengthened prompt: empty connections `{}` is never valid with 2+ nodes

**Pre-deploy validation gate** (`nodes/deploy.py`)
- Added `_validate_workflow_before_deploy()` — checks node IDs, types, webhook fields, connection coverage
- Guards against None `workflow_json` (crashes when assembler fails)

**Debugger + Deploy None guard** (`nodes/debugger.py`, `nodes/deploy.py`)
- Both now use `state.get("workflow_json")` instead of hard key access
- Prevents `AttributeError: 'NoneType'` when assembler produces no workflow

### Data Quality Fix

**ChromaDB node docs had empty parameter templates** (`boundary/scraper/`)
- `normalizer.py`: Stopped embedding useless `"parameters": {}` JSON skeleton in node docs
- Now includes actual scraped parameter names + descriptions in the embedded text
- `n8n_scraper.py`: Added Strategy 2 for parameter extraction — reads `<h3>` sub-headings under "Node parameters" `<h2>` sections (works for 111/580 nodes)
- Re-ingested 580 nodes into ChromaDB with enriched text
- Root cause: normalizer hardcoded `"parameters": {}` in the template, and the scraper only counted params without including them

### Commits

```
55ce5f8 fix(debugger): convert DebuggerOutput to dict to fix msgpack serialization crash
59d5336 fix(assembler): add connection validation + strengthen prompt to prevent empty connections
d503556 fix(deploy): add pre-deploy validation gate for node IDs, webhook paths, connections
9810241 fix(node-worker): add parameter validation + strengthen prompt to prevent empty params
51029ac fix(deploy,debugger): guard against None workflow_json when assembler fails
```
