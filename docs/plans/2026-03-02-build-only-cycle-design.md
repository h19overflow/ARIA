# Build-Only Cycle Design

**Date:** 2026-03-02
**Branch:** `feat/build-only-cycle`
**Status:** Approved

## Context

The current build cycle includes a test → debug → HITL-fix loop that is hard to stabilize because:
- n8n nodes may not be installed on the target instance
- Credentials can be misconfigured or confused between node types
- The webhook test path requires activation, triggering, and polling — brittle in practice

This design decouples **building** from **testing/debugging**. The goal is a reliable pipeline that produces a deployed (inactive) n8n workflow with an editor link. Testing/debugging becomes a separate future graph.

## New Graph Flow

```
node_planner → [fan-out] → node_worker(s) → assembler → deploy → END
```

- `deploy` is the terminal node
- On success: returns `n8n_workflow_id`, `n8n_workflow_url`, `status: "done"`
- On failure: returns `status: "failed"` with error details
- Workflow is deployed **inactive** (no auto-activation)

## File Deletions

### Node files (delete)
- `src/agentic_system/build_cycle/nodes/test.py`
- `src/agentic_system/build_cycle/nodes/debugger.py`
- `src/agentic_system/build_cycle/nodes/activate.py`
- `src/agentic_system/build_cycle/nodes/hitl_escalation.py`

### Module helpers (delete — only used by deleted nodes)
- `nodes/modules/_routers.py`
- `nodes/modules/_debugger_auth.py`
- `nodes/modules/_debugger_compact.py`
- `nodes/modules/_debugger_fix.py`
- `nodes/modules/_trigger_utils.py`

### Test file (delete — tests deleted routers)
- `tests/unit/test_build_cycle_graph.py`

## File Modifications

### `nodes/modules/_graph_wiring.py`
- Remove imports for: test, debugger, activate, hitl_escalation, _routers, _fan_out (mark_failed)
- Remove `mark_failed()` function
- `register_nodes()`: only register `node_planner`, `node_worker`, `assembler`, `deploy`
- `wire_edges()`: `planner → fan_out → worker → assembler → deploy → END`. No conditional edges after deploy.

### `nodes/deploy.py`
- On success: return `n8n_workflow_id`, `n8n_workflow_url`, `status: "done"`
- On failure: return `status: "failed"`, `execution_result` with error
- Remove `status == "fixing"` branch (no debugger to route to)
- Keep `_validate_workflow_before_deploy` pre-checks
- Add `n8n_workflow_url` construction: `f"{base_url}/workflow/{workflow_id}"`

### `src/agentic_system/shared/state.py`
- **Remove fields:** `execution_result`, `classified_error`, `fix_attempts`, `n8n_execution_id`, `webhook_url`, `paused_for_input`, `hitl_explanation`
- **Add field:** `n8n_workflow_url: str | None`

### Frontend

**`SuccessBanner.tsx`:**
- Remove webhook URL display + copy button
- Remove "Fixed N issues" text
- Show "Workflow created!" + "Open in n8n" button using `n8n_workflow_url`

**`BuildPage.tsx`:**
- Remove `FixEscalationPanel` rendering

## Files Unchanged
- `graph.py` — already just a shell
- `nodes/node_planner.py` — core, keep as-is
- `nodes/node_worker.py` — core, keep as-is
- `nodes/assembler.py` — core, keep as-is
- `nodes/modules/_fan_out.py` — keep
- `nodes/modules/_node_worker_helpers.py` — keep
- `nodes/modules/_credential_resolver.py` — keep
- API routes (`build.py`, `jobs.py`) — no changes needed
- `useBuild.ts` — handles done/error events already

## Verification

1. Run `python -c "from src.agentic_system.build_cycle.graph import build_build_cycle_graph; print('OK')"` — imports clean
2. Trigger a build via `POST /build` with a valid conversation → confirm SSE stream emits `node_start`/`node` events for planner, workers, assembler, deploy, then `done`
3. Confirm the `done` event payload includes `n8n_workflow_url`
4. Confirm the frontend SuccessBanner renders "Open in n8n" with the correct link
5. Confirm the workflow appears in n8n UI as **inactive**
