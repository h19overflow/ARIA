# ARIA Agentic System

A conversational agent plus a LangGraph build cycle that turn a plain-English request into a live, activated n8n workflow.

---

## End-to-end flow

```mermaid
flowchart TD
    U([User request]) --> CONV

    subgraph CONV [CONVERSATION]
        direction TB
        CA[Conversation Agent] -->|probe| Q[Ask user]
        Q --> CA
        CA -->|batch_notes / take_note| N[Update ConversationNotes]
        N --> CA
        CA -->|commit_notes| CRED[Credential Mode]
        CRED -->|scan_credentials| SC[Check n8n]
        SC -->|missing| ASK[Ask user for creds]
        ASK -->|save_credential| SC
        SC -->|all resolved| CP[commit_preflight]
    end

    CONV --> BC

    subgraph BC [BUILD CYCLE]
        direction TB
        RAG[RAG Retriever] --> PP[Phase Planner]
        PP --> ENG[Engineer]
        ENG --> DEP[Deploy] --> TST[Test]
        TST -->|more phases| ADV[Advance Phase] --> ENG
        TST -->|error| DBG[Debugger]
        DBG -->|fixed| DEP
        DBG -->|exhausted| ESC[HITL Escalation]
        ESC -->|manual fix| DEP
        ESC -->|replan or abort| FAIL[Fail]
        TST -->|done| ACT[Activate]
    end

    ACT --> DONE([Live workflow and webhook URL])

    style CA fill:#dbeafe,stroke:#3b82f6,color:#1e3a5f
    style PP fill:#dbeafe,stroke:#3b82f6,color:#1e3a5f
    style ENG fill:#dbeafe,stroke:#3b82f6,color:#1e3a5f
    style DBG fill:#dbeafe,stroke:#3b82f6,color:#1e3a5f
    style Q fill:#fef9c3,stroke:#ca8a04,color:#713f12
    style ASK fill:#fef9c3,stroke:#ca8a04,color:#713f12
    style ESC fill:#fef9c3,stroke:#ca8a04,color:#713f12
    style N fill:#f0fdf4,stroke:#16a34a,color:#14532d
    style CRED fill:#f0fdf4,stroke:#16a34a,color:#14532d
    style SC fill:#f0fdf4,stroke:#16a34a,color:#14532d
    style CP fill:#f0fdf4,stroke:#16a34a,color:#14532d
    style RAG fill:#f0fdf4,stroke:#16a34a,color:#14532d
    style DEP fill:#f0fdf4,stroke:#16a34a,color:#14532d
    style TST fill:#f0fdf4,stroke:#16a34a,color:#14532d
    style ADV fill:#f0fdf4,stroke:#16a34a,color:#14532d
    style ACT fill:#f0fdf4,stroke:#16a34a,color:#14532d
    style FAIL fill:#fef2f2,stroke:#dc2626,color:#7f1d1d
    style U fill:#f5f3ff,stroke:#7c3aed,color:#3b0764
    style DONE fill:#f5f3ff,stroke:#7c3aed,color:#3b0764
    style CONV fill:#f8fafc,stroke:#94a3b8
    style BC fill:#f8fafc,stroke:#94a3b8
```

**Blue = Agentic (LLM)** | **Yellow = Pauses for user** | **Green = Deterministic / API call**

---

## Conversation Agent + Build Cycle Graph

The system has two execution layers:

1. **Conversation Agent** — a `BaseAgent` (not a LangGraph graph) that handles requirements gathering and credential resolution in a single streaming chat. State persisted to Redis.
2. **Build Cycle Graph** — a LangGraph `StateGraph` compiled with `MemorySaver` that builds, deploys, tests, and self-heals the workflow.

```mermaid
flowchart LR
    FE["Frontend\n(React)"] <-->|SSE stream| API["FastAPI"]
    API --> CA["Conversation Agent\n(BaseAgent)"]
    CA -->|state| RD[(Redis)]
    RD --> BS["Build Service"]
    BS -->|ARIAState| BCG["Build Cycle Graph\n(MemorySaver)"]
    BCG -->|final state| API
    API -->|resume_value| BCG
```

The build service reads the committed `ConversationState` from Redis (`conversation:{id}`), converts it to `ARIAState`, and streams the build cycle graph.

---

## Conversation Agent — two modes

The `ConversationAgent` operates in two sequential modes within the same chat session:

### Mode 1: Requirements Gathering

Tools: `batch_notes`, `take_note`, `commit_notes`

The agent probes the user for workflow details (trigger, actions, destinations, constraints, integrations) and structures them into `ConversationNotes`. When requirements are complete, it calls `commit_notes` to finalize.

### Mode 2: Credential Gathering

Tools: `scan_credentials`, `get_credential_schema`, `save_credential`, `commit_preflight`

After `commit_notes`, the agent creates a **per-request agent graph** with credential tools bound to the required node types (no singleton mutation). It scans n8n for existing credentials, asks the user for missing ones, saves them, and calls `commit_preflight` when all are resolved.

| Tool | What It Does |
|---|---|
| `scan_credentials` | Checks n8n for saved credentials matching required node types |
| `get_credential_schema` | Fetches the field schema for a credential type from n8n |
| `save_credential` | Saves a credential to n8n with user-provided data |
| `commit_preflight` | Marks credentials as committed; enables build |

**Key files:**

```
conversation/
├── agent.py              # ConversationAgent — streaming, per-request credential graph
├── credential_tools.py   # scan_credentials (factory), get_credential_schema, save_credential, commit_preflight
├── schema_helpers.py     # is_secret_field, fields_from_schema, fetch_pending_details
├── schemas.py            # ConversationNotes (requirements + credential fields)
├── state.py              # ConversationState — Redis persistence with bounded fallback
├── tools.py              # batch_notes, take_note, commit_notes
├── prompts.py            # CONVERSATION_SYSTEM_PROMPT (base + credential section)
├── notes_updater.py      # State mutation helpers for all tool results
├── event_handlers.py     # SSE event dispatch, tool_call_id tracking
└── message_builders.py   # LangChain message construction from state
```

---

## Where user interaction happens

| Interaction | Phase | Trigger | User Action |
|---|---|---|---|
| Probing questions | Conversation | Agent needs clarification | Answer in chat |
| Credential request | Conversation | `scan_credentials` found missing creds | Provide API key / token in chat |
| `fix_exhausted` | Build Cycle | Debugger hit 3 fix attempts | Choose: retry / replan / abort |

---

## What streams to the UI and when

### Conversation

Token-by-token SSE streaming via `process_message()`. Tool events are emitted for each tool call:

```
token        → "What service triggers this workflow?"
tool_event   → { tool: "batch_notes", data: { count: 3, notes: [...] } }
tool_event   → { tool: "commit_notes", data: { summary: "..." } }
tool_event   → { tool: "scan_credentials", data: { resolved: [...], pending: [...] } }
tool_event   → { tool: "save_credential", data: { credential_type: "...", success: true } }
tool_event   → { tool: "commit_preflight", data: { committed: true } }
```

### Build Cycle

Per-node progress updates via SSE:

```
rag_retriever   →  "Retrieved 14 templates for 3 nodes"
phase_planner   →  "Linear pipeline → 3 phases: [GitHub Trigger], [IF], [Slack]"
engineer        →  "Phase 0: built 1 node (GitHub Trigger)"
deploy          →  "Deployed workflow wf-abc123"
test            →  "Execution success" / "Execution error: ..."
debugger        →  "Fix applied to Slack: corrected channel parameter format"
activate        →  "Activated. Webhook: https://localhost:5678/webhook/xyz"
```

---

## Sub-graph details

| Component | README |
|---|---|
| Build Cycle | [build_cycle/README.md](./build_cycle/README.md) |
