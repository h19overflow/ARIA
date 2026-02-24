# ARIA Agentic System

Two sequential LangGraph graphs that turn a plain-English request into a live, activated n8n workflow.

---

## End-to-end flow

```mermaid
flowchart TD
    U([User request]) --> PF

    subgraph PF [PREFLIGHT]
        direction TB
        ORC[Orchestrator] -->|clarify?| HC[Ask user]
        HC --> ORC
        ORC -->|commit| CS[Credential Scanner]
        CS -->|ambiguous| CA[User picks credential]
        CA --> CS
        CS -->|missing| CG[Credential Guide]
        CG --> SAV[User enters credential]
        SAV --> CS
        CS -->|resolved| HO[Handoff to BuildBlueprint]
    end

    PF --> BC

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

    style ORC fill:#dbeafe,stroke:#3b82f6,color:#1e3a5f
    style CS fill:#dbeafe,stroke:#3b82f6,color:#1e3a5f
    style CG fill:#dbeafe,stroke:#3b82f6,color:#1e3a5f
    style PP fill:#dbeafe,stroke:#3b82f6,color:#1e3a5f
    style ENG fill:#dbeafe,stroke:#3b82f6,color:#1e3a5f
    style DBG fill:#dbeafe,stroke:#3b82f6,color:#1e3a5f
    style HC fill:#fef9c3,stroke:#ca8a04,color:#713f12
    style CA fill:#fef9c3,stroke:#ca8a04,color:#713f12
    style SAV fill:#fef9c3,stroke:#ca8a04,color:#713f12
    style ESC fill:#fef9c3,stroke:#ca8a04,color:#713f12
    style HO fill:#f0fdf4,stroke:#16a34a,color:#14532d
    style RAG fill:#f0fdf4,stroke:#16a34a,color:#14532d
    style DEP fill:#f0fdf4,stroke:#16a34a,color:#14532d
    style TST fill:#f0fdf4,stroke:#16a34a,color:#14532d
    style ADV fill:#f0fdf4,stroke:#16a34a,color:#14532d
    style ACT fill:#f0fdf4,stroke:#16a34a,color:#14532d
    style FAIL fill:#fef2f2,stroke:#dc2626,color:#7f1d1d
    style U fill:#f5f3ff,stroke:#7c3aed,color:#3b0764
    style DONE fill:#f5f3ff,stroke:#7c3aed,color:#3b0764
    style PF fill:#f8fafc,stroke:#94a3b8
    style BC fill:#f8fafc,stroke:#94a3b8
```

**🤖 Blue = Agentic (LLM)** · **⏸️ Yellow = Pauses for user** · **🟢 Green = Deterministic / API call**

---

## Two separate graphs, not one

The two phases are compiled as independent LangGraph graphs, each with its own `MemorySaver` checkpointer. They run sequentially via `ARIAPipeline`.

```mermaid
flowchart LR
    API["FastAPI\nendpoint"] -->|initial state| PFG["Preflight Graph\n(MemorySaver A)"]
    PFG -->|final state| BCG["Build Cycle Graph\n(MemorySaver B)"]
    BCG -->|final state| API

    API -->|resume_value| PFG
    API -->|resume_value| BCG
```

> **Why two graphs?** A single nested graph deadlocks when `interrupt()` fires inside a compiled subgraph. Splitting them fixes this (BUG-6).

---

## Where user interaction happens

| Interrupt | Phase | Trigger | User action |
|---|---|---|---|
| `orchestrator_clarification` | Preflight | Intent is ambiguous | Answer a follow-up question |
| `credential_ambiguity` | Preflight | Multiple matching creds in n8n | Pick which credential to use |
| `credential_request` | Preflight | Credential doesn't exist | Enter API key / OAuth in n8n |
| `fix_exhausted` | Build Cycle | Debugger hit retry limit | Choose: manual fix / replan / abort |

---

## What streams to the UI and when

### Preflight
No token streaming. Updates arrive only at interrupts (the graph pauses and returns a payload).

### Build Cycle
Per-node progress updates via `stream_build_cycle()` → `on_node(name, update)`:

```
rag_retriever   →  "Retrieved 14 templates for 3 nodes"
phase_planner   →  "Linear pipeline → 3 phases: [GitHub Trigger], [IF], [Slack]"
engineer        →  "Phase 0: built 1 node (GitHub Trigger)"
deploy          →  "Deployed workflow wf-abc123"
test            →  "Execution success" / "Execution error: ..."
debugger        →  "Fix applied to Slack: corrected channel parameter format"
advance_phase   →  (internal state update)
engineer        →  "Phase 1: built 1 node (IF)"
...
activate        →  "Activated. Webhook: https://localhost:5678/webhook/xyz"
```

> Individual LLM token streaming (character-by-character) is not used. Each node fires once when complete.

---

## Sub-graph details

| Graph | README |
|---|---|
| Preflight | [preflight/README.md](./preflight/README.md) |
| Build Cycle | [build_cycle/README.md](./build_cycle/README.md) |
