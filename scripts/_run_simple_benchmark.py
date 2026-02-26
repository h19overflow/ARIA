"""Quick 3-fixture benchmark — simple tier only. Run directly: python scripts/_run_simple_benchmark.py"""
from __future__ import annotations

import asyncio
import json
import sys
import time
import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from langgraph.errors import GraphInterrupt
from src.agentic_system.build_cycle.graph import build_build_cycle_graph
from src.agentic_system.build_cycle.nodes._trigger_utils import detect_trigger_type, extract_webhook_path
from src.boundary.n8n.client import N8nClient
from scripts._benchmark_build_fixtures import FIXTURES

SIMPLE = [f for f in FIXTURES if f["tier"] == "simple"]


def make_state(bp: dict) -> dict:
    return {
        "messages": [], "intent": bp["intent"], "required_nodes": bp["required_nodes"],
        "resolved_credential_ids": bp.get("credential_ids", {}), "pending_credential_types": [],
        "credential_guide_payload": None, "build_blueprint": bp, "topology": bp.get("topology"),
        "user_description": bp.get("user_description", ""), "intent_summary": "",
        "conversation_notes": None, "node_templates": [], "workflow_json": None,
        "n8n_workflow_id": None, "n8n_execution_id": None, "execution_result": None,
        "classified_error": None, "fix_attempts": 0, "webhook_url": None, "status": "building",
        "build_phase": 0, "total_phases": 0, "phase_node_map": [], "paused_for_input": False,
        "hitl_explanation": None, "orchestrator_decision": "", "pending_question": "",
        "orchestrator_turns": 0,
    }


async def cleanup_workflow(workflow_id: str) -> None:
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


async def verify_execution(workflow_id: str, workflow_json: dict) -> dict:
    """Verify functional correctness based on trigger type.

    Webhook: fire webhook + poll execution.
    Schedule/other: activation-only — n8n REST API on this instance does not support
    manual workflow execution, so a clean activation is treated as pass.
    """
    trigger_type = detect_trigger_type(workflow_json)
    if trigger_type != "webhook":
        # Activation already succeeded (test_node activated it) — treat as pass
        return {"status": "success", "note": "activation-only verification"}

    client = N8nClient()
    await client.connect()
    try:
        path = extract_webhook_path(workflow_json)
        await client.trigger_webhook(path, payload={"test": True})
        return await client.poll_execution(workflow_id, timeout=30.0)
    finally:
        await client.disconnect()


async def run_fixture(fixture: dict, graph) -> dict:
    bp = fixture["blueprint"]
    state = make_state(bp)
    t0 = time.time()
    final: dict = dict(state)

    try:
        async for event in graph.astream(state, stream_mode="updates"):
            for node_name, upd in event.items():
                elapsed = round(time.time() - t0, 1)
                status = upd.get("status", "?")
                print(f"    [{elapsed}s] {node_name}: {status}")
                # Print debugger messages so we can see what errors the LLM is seeing
                for msg in upd.get("messages", []):
                    content = getattr(msg, "content", str(msg))
                    if "[Debugger]" in content or "[Test] Error" in content:
                        print(f"      >> {content}")
                final.update(upd)
    except GraphInterrupt:
        # HITL escalation raised — no checkpointer in benchmark context, treat as FAIL
        elapsed = round(time.time() - t0, 1)
        workflow_json = final.get("workflow_json") or {}
        workflow_id = final.get("n8n_workflow_id")
        if workflow_id:
            await cleanup_workflow(workflow_id)
        return _make_result(fixture, "FAIL", "hitl_escalated", "not_run",
                            workflow_json, final, elapsed,
                            final.get("build_phase", 0) + 1, final.get("fix_attempts", 0))
    except BaseException as exc:
        elapsed = round(time.time() - t0, 1)
        workflow_id = final.get("n8n_workflow_id")
        if workflow_id:
            await cleanup_workflow(workflow_id)
        return _make_result(fixture, "FAIL", f"exception: {exc}", "error", None, {}, elapsed, 0, 0)

    elapsed = round(time.time() - t0, 1)
    build_status = final.get("status", "unknown")
    workflow_id = final.get("n8n_workflow_id")
    workflow_json = final.get("workflow_json") or {}

    if build_status != "done" or not workflow_id:
        if workflow_id:
            await cleanup_workflow(workflow_id)
        return _make_result(fixture, "FAIL", f"build_status={build_status}", "not_run",
                            workflow_json, final, elapsed,
                            final.get("build_phase", 0) + 1, final.get("fix_attempts", 0))

    exec_status = "error"
    exec_error = None
    try:
        raw = await verify_execution(workflow_id, workflow_json)
        exec_status = raw.get("status", "error")
    except Exception as exc:
        exec_error = str(exc)

    await cleanup_workflow(workflow_id)

    passed = exec_status == "success"
    return _make_result(
        fixture,
        "PASS" if passed else "FAIL",
        None if passed else f"exec_failed: {exec_error or exec_status}",
        exec_status, workflow_json, final, elapsed,
        final.get("build_phase", 0) + 1, final.get("fix_attempts", 0),
    )


def _make_result(
    fixture: dict, status: str, reason: str | None, exec_status: str,
    workflow_json: dict, final: dict, elapsed: float, phases: int, fixes: int,
) -> dict:
    trigger = detect_trigger_type(workflow_json) if workflow_json else None
    return {
        "name": fixture["name"],
        "tier": fixture["tier"],
        "status": status,
        "reason": reason,
        "elapsed_seconds": elapsed,
        "execution_status": exec_status,
        "actual_trigger_type": trigger,
        "expected_trigger_type": fixture["expected_trigger_type"],
        "trigger_correct": trigger == fixture["expected_trigger_type"],
        "actual_node_count": len((workflow_json or {}).get("nodes", [])),
        "expected_node_count": fixture["expected_node_count"],
        "phases_used": phases,
        "fix_attempts_total": fixes,
        "classified_error": final.get("classified_error"),
        "workflow_json": workflow_json,
    }


async def main() -> None:
    print("=" * 60)
    print("  ARIA Build Cycle — Simple Fixture Benchmark (3 fixtures)")
    print("=" * 60)

    graph = build_build_cycle_graph().compile()
    results: list[dict] = []
    total_t0 = time.time()

    for i, fixture in enumerate(SIMPLE, 1):
        print(f"\n[{i}/3] {fixture['name']} ({fixture['tier']})")
        result = await run_fixture(fixture, graph)
        icon = "PASS" if result["status"] == "PASS" else "FAIL"
        print(f"  => {icon} | exec={result['execution_status']} | "
              f"trigger={result['actual_trigger_type']} (correct={result['trigger_correct']}) | "
              f"nodes={result['actual_node_count']} | phases={result['phases_used']} | "
              f"fixes={result['fix_attempts_total']} | {result['elapsed_seconds']}s")
        if result["reason"]:
            print(f"     reason: {result['reason']}")
        results.append(result)

    total_elapsed = round(time.time() - total_t0, 1)
    passed = sum(1 for r in results if r["status"] == "PASS")

    print(f"\n{'=' * 60}")
    print(f"  RESULTS: {passed}/{len(results)} passed  ({total_elapsed}s total)")
    print(f"{'=' * 60}")

    out_dir = PROJECT_ROOT / "scripts" / "outputs"
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_file = out_dir / f"benchmark_simple_{ts}.json"
    out_file.write_text(json.dumps({"passed": passed, "total": len(results), "results": results}, indent=2))
    print(f"  Saved: {out_file}")


if __name__ == "__main__":
    asyncio.run(main())
