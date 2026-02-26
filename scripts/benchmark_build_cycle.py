"""Build Cycle Benchmark — runs 9 fixtures end-to-end and produces a rich JSON + terminal report.

Usage:
    python scripts/benchmark_build_cycle.py

Output:
    scripts/outputs/benchmark_build_cycle_<timestamp>.json
"""
from __future__ import annotations

import asyncio
import json
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.agentic_system.shared.state import ARIAState
from src.agentic_system.build_cycle.graph import build_build_cycle_graph
from src.agentic_system.build_cycle.nodes._trigger_utils import detect_trigger_type
from src.boundary.n8n.client import N8nClient
from scripts._benchmark_build_fixtures import FIXTURES


# ── State builder ────────────────────────────────────────────

def _make_initial_state(blueprint: dict) -> dict:
    """Build the minimum ARIAState for a benchmark run."""
    return {
        "messages": [],
        "intent": blueprint["intent"],
        "required_nodes": blueprint["required_nodes"],
        "resolved_credential_ids": blueprint.get("credential_ids", {}),
        "pending_credential_types": [],
        "credential_guide_payload": None,
        "build_blueprint": blueprint,
        "topology": blueprint.get("topology"),
        "user_description": blueprint.get("user_description", ""),
        "intent_summary": "",
        "conversation_notes": None,
        "node_templates": [],
        "workflow_json": None,
        "n8n_workflow_id": None,
        "n8n_execution_id": None,
        "execution_result": None,
        "classified_error": None,
        "fix_attempts": 0,
        "webhook_url": None,
        "status": "building",
        "build_phase": 0,
        "total_phases": 0,
        "phase_node_map": [],
        "paused_for_input": False,
        "hitl_explanation": None,
        "orchestrator_decision": "",
        "pending_question": "",
        "orchestrator_turns": 0,
    }


# ── n8n helpers ────────────────────────────────────────────

async def _run_manual_execution(workflow_id: str) -> dict:
    """Trigger a manual execution and poll for result."""
    client = N8nClient()
    await client.connect()
    try:
        await client.run_workflow(workflow_id)
        return await client.poll_execution(workflow_id, timeout=30.0)
    finally:
        await client.disconnect()


async def _cleanup_workflow(workflow_id: str) -> None:
    """Deactivate and delete a workflow, swallowing errors."""
    client = N8nClient()
    await client.connect()
    try:
        try:
            await client.deactivate_workflow(workflow_id)
        except Exception:
            pass
        await client.delete_workflow(workflow_id)
    except Exception:
        pass
    finally:
        await client.disconnect()


# ── Per-fixture runner ───────────────────────────────────────────

async def run_fixture(fixture: dict, graph) -> dict:
    """Run one fixture through the full build cycle. Returns a rich result dict."""
    name = fixture["name"]
    tier = fixture["tier"]
    blueprint = fixture["blueprint"]

    state = _make_initial_state(blueprint)
    t0 = time.time()

    trace: list[dict] = []
    final_state: dict = dict(state)

    try:
        async for event in graph.astream(state, stream_mode="updates"):
            for node_name, update in event.items():
                elapsed = round(time.time() - t0, 1)
                trace.append({
                    "node": node_name,
                    "elapsed_seconds": elapsed,
                    "status": update.get("status"),
                    "fix_attempts": update.get("fix_attempts"),
                    "build_phase": update.get("build_phase"),
                })
                final_state.update(update)
    except Exception as exc:
        elapsed = round(time.time() - t0, 1)
        return _failure_result(fixture, elapsed, str(exc), traceback.format_exc(), trace)

    elapsed = round(time.time() - t0, 1)
    build_status = final_state.get("status", "unknown")
    workflow_id = final_state.get("n8n_workflow_id")
    workflow_json = final_state.get("workflow_json") or {}

    if build_status != "done" or not workflow_id:
        reason = _classify_failure(build_status, final_state)
        result = _build_result(fixture, elapsed, "FAIL", reason, final_state, workflow_json, trace)
        if workflow_id:
            await _cleanup_workflow(workflow_id)
        return result

    exec_result = None
    exec_status = "skipped"
    exec_error = None
    try:
        raw_exec = await _run_manual_execution(workflow_id)
        exec_status = raw_exec.get("status", "error")
        exec_result = raw_exec
    except Exception as exc:
        exec_status = "error"
        exec_error = str(exc)

    await _cleanup_workflow(workflow_id)

    passed = exec_status == "success"
    reason = None if passed else f"execution_failed: {exec_error or exec_status}"

    actual_trigger = detect_trigger_type(workflow_json)
    node_count = len(workflow_json.get("nodes", []))

    return {
        "name": name,
        "tier": tier,
        "status": "PASS" if passed else "FAIL",
        "reason": reason,
        "elapsed_seconds": elapsed,
        "build_status": build_status,
        "phases_used": final_state.get("build_phase", 0) + 1,
        "fix_attempts_total": final_state.get("fix_attempts", 0),
        "expected_trigger_type": fixture["expected_trigger_type"],
        "actual_trigger_type": actual_trigger,
        "trigger_correct": actual_trigger == fixture["expected_trigger_type"],
        "expected_node_count": fixture["expected_node_count"],
        "actual_node_count": node_count,
        "execution_status": exec_status,
        "workflow_id": workflow_id,
        "workflow_json": workflow_json,
        "execution_result": exec_result,
        "classified_error": final_state.get("classified_error"),
        "trace": trace,
        "error": exec_error,
    }


def _classify_failure(build_status: str, state: dict) -> str:
    """Map build_status to a human-readable failure reason tag."""
    if build_status == "failed":
        err = state.get("classified_error") or {}
        return f"build_failed: {err.get('type', 'unknown')} in {err.get('node_name', 'unknown')}"
    if build_status == "fixing":
        return "hitl_escalated"
    if build_status == "replanning":
        return "replan_requested"
    return f"unexpected_status: {build_status}"


def _failure_result(
    fixture: dict, elapsed: float, error: str, tb: str, trace: list[dict],
) -> dict:
    return {
        "name": fixture["name"],
        "tier": fixture["tier"],
        "status": "FAIL",
        "reason": f"exception: {error[:200]}",
        "elapsed_seconds": elapsed,
        "build_status": "exception",
        "phases_used": 0,
        "fix_attempts_total": 0,
        "expected_trigger_type": fixture["expected_trigger_type"],
        "actual_trigger_type": None,
        "trigger_correct": False,
        "expected_node_count": fixture["expected_node_count"],
        "actual_node_count": 0,
        "execution_status": "error",
        "workflow_id": None,
        "workflow_json": None,
        "execution_result": None,
        "classified_error": None,
        "trace": trace,
        "error": error,
        "traceback": tb,
    }


def _build_result(
    fixture: dict,
    elapsed: float,
    status: str,
    reason: str | None,
    state: dict,
    workflow_json: dict,
    trace: list[dict],
) -> dict:
    actual_trigger = detect_trigger_type(workflow_json) if workflow_json else None
    node_count = len(workflow_json.get("nodes", [])) if workflow_json else 0
    return {
        "name": fixture["name"],
        "tier": fixture["tier"],
        "status": status,
        "reason": reason,
        "elapsed_seconds": elapsed,
        "build_status": state.get("status"),
        "phases_used": state.get("build_phase", 0) + 1,
        "fix_attempts_total": state.get("fix_attempts", 0),
        "expected_trigger_type": fixture["expected_trigger_type"],
        "actual_trigger_type": actual_trigger,
        "trigger_correct": actual_trigger == fixture["expected_trigger_type"],
        "expected_node_count": fixture["expected_node_count"],
        "actual_node_count": node_count,
        "execution_status": "not_run",
        "workflow_id": state.get("n8n_workflow_id"),
        "workflow_json": workflow_json,
        "execution_result": None,
        "classified_error": state.get("classified_error"),
        "trace": trace,
        "error": None,
    }


# ── Terminal report ─────────────────────────────────────────────────────

def _print_summary(results: list[dict], total_elapsed: float) -> None:
    passed = sum(1 for r in results if r["status"] == "PASS")
    print(f"
{'=' * 72}")
    print("  BUILD CYCLE BENCHMARK RESULTS")
    print(f"{'=' * 72}")
    header = f"  {'Name':<42} {'Tier':<8} {'Result':<6} {'Phases':<7} {'Fixes':<6} Exec"
    print(header)
    print(f"  {'-' * 70}")
    for r in results:
        icon = "PASS" if r["status"] == "PASS" else "FAIL"
        trigger_ok = "ok" if r["trigger_correct"] else "WRONG"
        print(
            f"  {r['name']:<42} {r['tier']:<8} {icon:<6} "
            f"{r['phases_used']:<7} {r['fix_attempts_total']:<6} {r['execution_status']}"
            f"  [trigger {trigger_ok}]"
        )
        if r["reason"]:
            print(f"    -> {r['reason']}")
    print(f"
  Passed: {passed}/{len(results)}")
    print(f"  Total time: {round(total_elapsed, 1)}s")
    print(f"{'=' * 72}")


# ── Main ───────────────────────────────────────────────────────────────────

async def main() -> None:
    print("=" * 72)
    print("  ARIA Build Cycle Benchmark")
    print("=" * 72)

    graph = build_build_cycle_graph().compile()
    results: list[dict] = []
    total_t0 = time.time()

    for i, fixture in enumerate(FIXTURES, 1):
        print(f"
[{i}/{len(FIXTURES)}] {fixture['name']} ({fixture['tier']})")
        result = await run_fixture(fixture, graph)
        icon = "PASS" if result["status"] == "PASS" else "FAIL"
        print(f"  {icon} -- {result['elapsed_seconds']}s -- exec: {result['execution_status']}")
        if result.get("reason"):
            print(f"  Reason: {result['reason']}")
        results.append(result)

    total_elapsed = time.time() - total_t0
    _print_summary(results, total_elapsed)

    output_dir = PROJECT_ROOT / "scripts" / "outputs"
    output_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"benchmark_build_cycle_{ts}.json"
    output_file.write_text(json.dumps({
        "timestamp": ts,
        "total_elapsed_seconds": round(total_elapsed, 1),
        "passed": sum(1 for r in results if r["status"] == "PASS"),
        "total": len(results),
        "results": results,
    }, indent=2))
    print(f"
  Report saved: {output_file}")


if __name__ == "__main__":
    asyncio.run(main())
