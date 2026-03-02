# Build Cycle — Reference

The Build Cycle takes the committed `BuildBlueprint` from Phase 0 and turns it into a **live, tested, activated n8n workflow**. It runs as a LangGraph subgraph.

> **Upstream requirement:** `conversation:{id}` Redis key must have `committed=true` AND `credentials_committed=true` before the build cycle starts.

---

## 1. Component Map — Orchestration Layer

What `graph.py` owns and how the 8 nodes relate to each other at the routing level.

```mermaid
graph LR
    GR["graph.py\nbuild_build_cycle_graph()"]

    NP["node_planner\nentry point"]
    NW["node_worker\n(parallel fan-out)"]
    AS["assembler\nfan-in"]
    DP["deploy"]
    TS["test"]
    DB["debugger"]
    AC["activate"]
    HI["hitl_escalation"]
    FL["fail\nterminal"]

    GR --> NP
    NP -->|"Send API\none per NodeSpec"| NW
    NW --> AS
    AS --> DP
    DP -->|"status=testing"| TS
    DP -->|"status=fixing"| DB
    TS -->|"success"| AC
    TS -->|"error"| DB
    DB -->|"rate_limit"| TS
    DB -->|"fixable + budget"| DP
    DB -->|"unfixable\nor budget=0"| HI
    HI -->|"retry"| TS
    HI -->|"replan/abort"| FL
    AC --> DONE(["done"])
    FL --> FAIL(["failed"])
```

---

## 2. Component Map — Node Internals

What each node file imports and depends on.

```mermaid
graph TD
    subgraph Agentic["Agentic Nodes (LLM)"]
        NP["node_planner.py"]
        NW["node_worker.py"]
        AS["assembler.py"]
        DB["debugger.py"]
        HI["hitl_escalation.py"]
    end

    subgraph Deterministic["Deterministic Nodes (API only)"]
        DP["deploy.py"]
        TS["test.py"]
        AC["activate.py"]
    end

    subgraph Helpers["Private Helpers (_)"]
        CR["_credential_resolver.py"]
        DA["_debugger_auth.py"]
        DF["_debugger_fix.py"]
        DC["_debugger_compact.py"]
        TU["_trigger_utils.py"]
    end

    NP --> CR
    DB --> DA & DF & DC
    DA --> CR
    TS --> TU
    AC --> TU
```


---

## 4. Workflow — Build Path (Happy)

The path when everything works first time.

```mermaid
flowchart TD
    A(["BuildBlueprint"])
    B["Node Planner\n🤖 RAG search → NodePlan\n+ cycle detection"]
    C{{"Fan-out\nSend API"}}
    D["Node Workers × N\n🤖 parallel\none LLM call each"]
    E["Assembler\n🤖 validate + wire connections\n→ workflow_json"]
    F["Deploy\n⚙️ POST to n8n\n→ workflow_id"]
    G["Test\n⚙️ activate → trigger → poll"]
    H["Activate\n⚙️ stay active\n→ webhook_url"]
    Z(["✅ done"])

    A --> B --> C --> D --> E --> F --> G --> H --> Z
```

---

## 5. Workflow — Fix / Debug Path

The path when something goes wrong after assembly.

```mermaid
flowchart TD
    AS_ERR["Assembler\nvalidation failed\nor dangling edge"]
    DP_ERR["Deploy\nHTTP error from n8n"]
    TS_ERR["Test\nexecution error"]

    DB["Debugger 🤖\nPhase 1: DiagnosticResearcher\nPhase 2: FixComposer\n→ patch workflow_json"]

    CHK{"fix_attempts < 3\nAND fixable type?"}

    DP2["Deploy again\n(updated workflow)"]
    TS2["Test again"]

    HI["HITL Escalation ⏸️\ninterrupt() — graph pauses\nexplain error in plain English"]

    USR{"User action"}

    RETRY["retry\n(user fixed in n8n UI)"]
    ABORT["replan / abort"]

    AS_ERR & DP_ERR & TS_ERR --> DB
    DB --> CHK
    CHK -->|"yes"| DP2
    CHK -->|"no"| HI
    DP2 --> TS2
    TS2 -->|"still failing"| DB
    TS2 -->|"success"| DONE(["✅ done"])
    HI --> USR
    USR --> RETRY --> TS2
    USR --> ABORT --> FAIL(["❌ failed"])
```

---

## 6. Sequence — Node Planner (Two-Phase)

What happens inside the planner before any workers fire.

```mermaid
sequenceDiagram
    participant NP as Node Planner
    participant ND as NodeDiscovery
    participant R as Researcher Agent
    participant CD as ChromaDB
    participant C as Composer Agent

    NP->>ND: discover_installed_node_prefixes()
    ND-->>NP: ["n8n-nodes-base", ...]

    note over R: Phase 1
    NP->>R: intent + topology + packages
    R->>CD: search_n8n_nodes("gmail")
    R->>CD: search_n8n_nodes("webhook")
    CD-->>R: node docs
    R-->>NP: catalog (markdown)

    note over C: Phase 2
    NP->>C: catalog + intent
    C-->>NP: NodePlan {nodes, edges}

    alt cycle detected
        NP->>C: retry with error context
        C-->>NP: revised NodePlan
    end

    NP->>NP: resolve_node_credentials()
    NP-->>NP: nodes_to_build[]
```

---

## 7. Sequence — Workers + Assembler (Fan-Out / Fan-In)

```mermaid
sequenceDiagram
    participant GP as graph.py
    participant WA as Worker A
    participant WB as Worker B
    participant CD as ChromaDB
    participant AS as Assembler

    par Fan-out (parallel)
        GP->>WA: NodeSpec{Gmail}
        WA->>CD: search_n8n_nodes("gmail parameters")
        CD-->>WA: schema
        WA-->>GP: NodeResult {node_json, validation_passed: true}
    and
        GP->>WB: NodeSpec{Webhook}
        WB->>CD: search_n8n_nodes("webhook parameters")
        CD-->>WB: schema
        WB-->>GP: NodeResult {node_json, validation_passed: true}
    end

    GP->>AS: all node_build_results
    AS->>AS: validate results + check dangling edges

    alt any validation_passed=false
        AS-->>GP: status=fixing → route to Debugger
    else all pass
        AS->>CD: search connections format (if branching)
        AS-->>GP: workflow_json
    end
```

---

## 8. Sequence — Debugger (Two-Phase Fix)

```mermaid
sequenceDiagram
    participant GP as graph.py
    participant DB as Debugger
    participant CD as ChromaDB

    GP->>DB: execution_result {error, node_name}

    alt auth error (401/403/unauthorized)
        DB->>DB: _try_attach_credentials()
        DB-->>GP: patched workflow_json, status=building
    else all other errors
        note over DB: Phase 1 — DiagnosticResearcher
        DB->>CD: search_n8n_nodes(failing node type)
        CD-->>DB: correct schema docs
        DB-->>DB: diagnostic_report

        note over DB: Phase 2 — FixComposer
        DB-->>DB: DebuggerOutput {fixed_nodes, added_nodes, ...}
        DB->>DB: _apply_full_fix(workflow_json)
        DB-->>GP: patched workflow_json, fix_attempts+1
    end
```

---

## 9. Sequence — HITL Escalation

```mermaid
sequenceDiagram
    participant GP as graph.py
    participant HI as HITL Node
    participant LLM as HITLExplainer
    participant UI as User

    GP->>HI: fix_attempts=3, classified_error
    HI->>LLM: generate plain-English explanation
    LLM-->>HI: "The Gmail node failed because..."

    HI->>UI: interrupt() — graph pauses
    note over UI: Options: retry / replan / discuss / abort

    opt user asks a question
        UI-->>HI: {action: "discuss", message: "..."}
        HI->>LLM: answer question in context
        LLM-->>HI: answer
        HI->>UI: interrupt() again with updated explanation
    end

    UI-->>HI: {action: "retry"}
    HI-->>GP: fix_attempts=0, status=testing
```

---

## 10. Failure Map — Build Time

Failures that happen before the workflow reaches n8n.

```mermaid
graph TD
    subgraph Z0["Phase 0 Handoff"]
        A["intent missing\nor empty"]
        B["required_integrations\nis a CSV string\nnot a list"]
        C["credentials_committed=false\ncredential_id=None on all specs"]
    end

    subgraph Z1["Node Planner"]
        D["ChromaDB down\n→ empty catalog"]
        E["Composer outputs\ncyclic edges\n3 retries exhausted"]
        F["Node type not\nin installed packages"]
    end

    subgraph Z2["Node Workers"]
        G["Worker omits\nrequired parameters\nvalidation_passed=false"]
        H["Webhook node built\nwithout webhookId UUID"]
        I["Credential attached to\nwrong credential_type key"]
    end

    subgraph Z3["Assembler"]
        J["Wrong connections\nfor If/Switch branches\n(silent — no error)"]
        K["Dangling edge:\nnode name mismatch\nbetween planner + worker"]
    end

    A -->|"_empty_plan()\nno nodes built"| SKIP["build skipped"]
    B -->|"planner builds\nwrong nodes"| D
    C -->|"auth errors\nat test time"| AUTH["auth failure\nat test"]

    D -->|"Composer guesses types\nnot in installed list"| F
    E -->|"error_plan()\nescalates to HITL"| HITL["HITL"]
    F -->|"n8n rejects\nNode type not found"| N8ERR["deploy 400"]

    G -->|"Assembler short-circuits\nto debugger"| DBG["debugger"]
    H -->|"webhook unreachable\nin production"| PROD["silent prod failure"]
    I -->|"auth error at test"| AUTH

    J -->|"logic routes wrong\nno error at deploy"| PROD
    K -->|"Assembler dangling check\nroutes to debugger"| DBG
```

---

## 11. Failure Map — Runtime (Deploy → Test → Debug)

Failures that happen once the workflow reaches n8n.

```mermaid
graph TD
    subgraph Z4["Deploy"]
        A["n8n_workflow_id=None\nafter network error"]
        B["workflow references\nmissing credential"]
        C["'id' field sent\non PUT update\n(read-only)"]
    end

    subgraph Z5["Test"]
        D["webhook path not set\n→ extract returns 'test-webhook'\n→ poll finds no execution"]
        E["poll_execution\ntimes out at 30s"]
        F["delayed errors\nnot detected\n(list_executions not implemented)"]
    end

    subgraph Z6["Debugger"]
        G["auth fast-path loops:\ncredential attached\nbut still wrong"]
        H["FixComposer patches\nwrong node\n(name mismatch)"]
        I["workflow grows with\neach debug loop\nprompt too large"]
    end

    subgraph Z7["HITL"]
        J["frontend doesn't call\nPOST /jobs/id/resume\n→ job hangs forever"]
        K["user retries without\nfixing anything\n→ 3 more identical failures"]
    end

    A -->|"test crashes\nKeyError: n8n_workflow_id"| CRASH["runtime crash"]
    B -->|"n8n 400\nat deploy"| DBG["debugger"]
    C -->|"n8n 400\nat update"| DBG

    D -->|"false failure\nstarts debug loop"| DBG
    E -->|"false timeout error\nto debugger"| DBG
    F -->|"workflow reported done\nbut broken in prod"| PROD["silent prod failure"]

    G -->|"3 fix attempts consumed\non auth alone"| HITL["HITL escalation"]
    H -->|"fix does nothing\nnext test fails again"| LOOP["debug loop waste"]
    I -->|"LLM truncates prompt\nbad fix generated"| LOOP

    J -->|"job stuck\npaused_for_input=True"| HANG["hung job"]
    K -->|"hits HITL again\nimmediately"| HITL
```

### Top Failures — Ranked by Impact

| # | Zone | What goes wrong | How to spot it |
|---|---|---|---|
| 1 | Phase 0 handoff | `required_integrations` is `"Gmail, Slack"` not `["Gmail", "Slack"]` | Check `build_blueprint.topology` in state dump |
| 2 | Test | `webhook_path` not set → poll finds no execution → false failure | `workflow_json.nodes[0].parameters.path` is empty |
| 3 | Deploy | `n8n_workflow_id=None` after network error → test crashes | `KeyError: n8n_workflow_id` in logs |
| 4 | Workers | Node type not installed → n8n rejects deploy | Planner logs `[unknown_nodes_error]` |
| 5 | Debugger | Auth fast-path attaches credential that's still invalid → loops | `fix_attempts` hits 3 with all `type: "auth"` |
| 6 | HITL | Frontend never calls `/resume` → job hangs | Job status frozen at `hitl_escalation` |
| 7 | Assembler | Wrong `If`/`Switch` connections — no error raised | Inspect `workflow_json.connections` manually |
| 8 | Test | Delayed errors not detected (`list_executions` not implemented) | Check n8n execution logs after activation |

---

## 12. Node Reference

| Node | File | Agentic? | Pauses? | Plain English |
|---|---|---|---|---|
| **Node Planner** | `nodes/node_planner.py` | Yes — 2 LLM phases | No | Phase 1 searches ChromaDB for node docs. Phase 2 turns those docs into a structured build plan (nodes + connections). Detects cycles, retries up to 3×. |
| **Node Worker** | `nodes/node_worker.py` | Yes — 1 LLM + tool | No | One per node, all run in parallel. Looks up node schema in ChromaDB, fills in all parameters, returns a complete n8n node JSON. |
| **Assembler** | `nodes/assembler.py` | Yes — 1 LLM + tool | No | Waits for all workers. Validates results. If any failed → Debugger. Otherwise builds the connections between nodes and produces the final `workflow_json`. |
| **Deploy** | `nodes/deploy.py` | No | No | POST (new) or PUT (fix) the workflow to n8n. Captures the workflow ID. |
| **Test** | `nodes/test.py` | No | No | Webhook: activate → fire test request → poll for result. Non-webhook: activation = pass. |
| **Debugger** | `nodes/debugger.py` | Yes — 2 LLM phases | No | Auth fast-path skips LLM if it's a missing credential. Otherwise: Phase 1 researches the error, Phase 2 generates a structured fix (patch params, swap node type, add/remove nodes, rewire connections). |
| **Activate** | `nodes/activate.py` | No | No | Permanently activates the workflow. Returns the live webhook URL. |
| **HITL Escalation** | `nodes/hitl_escalation.py` | Yes — explanation only | **Yes** | Generates plain-English error explanation. Pauses graph via `interrupt()`. User decides: retry / replan / discuss / abort. |

---

## 13. Routing Logic

All routing lives in `graph.py`. Each function reads one or two state keys.

| Router | Key read | Routes to |
|---|---|---|
| `fan_out_nodes` (line 23) | `nodes_to_build` | `node_worker` × N via Send API |
| `_route_deploy_result` (line 62) | `state.status` | `test` or `debugger` |
| `_route_test_result` (line 38) | `execution_result.status` | `activate` or `debugger` |
| `_route_debugger_result` (line 46) | `classified_error.type` + `fix_attempts` | `test`, `deploy`, or `hitl_fix_escalation` |
| `_route_hitl_decision` (line 69) | `state.status` after resume | `deploy`, `test`, or `fail` |

**Fix budget:** `MAX_FIX_ATTEMPTS = 3` (`graph.py:19`). Debugger increments before routing — when `fix_attempts == 3` the router sends to HITL.

**Fixable types:** `{"schema", "logic", "missing_node", "auth"}` (`graph.py:20`). Any other type → HITL immediately regardless of budget.
