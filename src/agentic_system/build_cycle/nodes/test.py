"""Build Cycle Test — activate, trigger webhook or run manually, poll, deactivate on failure."""
from __future__ import annotations

import httpx
from langchain_core.messages import HumanMessage

from src.agentic_system.shared.state import ARIAState, ExecutionResult
from src.boundary.n8n.client import N8nClient
from src.agentic_system.build_cycle.nodes._trigger_utils import (
    detect_trigger_type,
    extract_webhook_path,
)


async def test_node(state: ARIAState) -> dict:
    """Activate workflow, fire it (webhook or manual run), poll result, deactivate on failure."""
    workflow_id = state["n8n_workflow_id"]
    workflow_json = state["workflow_json"]
    trigger_type = detect_trigger_type(workflow_json)

    client = N8nClient()
    await client.connect()
    try:
        await client.activate_workflow(workflow_id)
        await _fire_workflow(client, workflow_id, workflow_json, trigger_type)
        execution = await client.poll_execution(workflow_id, timeout=30.0)
        exec_result = _parse_execution(execution)
        if exec_result["status"] != "success":
            await _safe_deactivate(client, workflow_id)
    except httpx.HTTPStatusError as exc:
        await _safe_deactivate(client, workflow_id)
        body = exc.response.json() if exc.response else {}
        node_name = body.get("context", {}).get("nodeName", "unknown")
        return _error_result(body.get("message", str(exc)), node_name=node_name)
    except Exception as exc:
        await _safe_deactivate(client, workflow_id)
        return _error_result(str(exc))
    finally:
        await client.disconnect()

    is_success = exec_result["status"] == "success"
    return {
        "execution_result": exec_result,
        "n8n_execution_id": execution.get("id", ""),
        "status": "done" if is_success else "fixing",
        "messages": [HumanMessage(
            content=f"[Test] Execution {exec_result['status']}: {execution.get('id', 'unknown')}"
        )],
    }


async def _fire_workflow(
    client: N8nClient,
    workflow_id: str,
    workflow_json: dict,
    trigger_type: str,
) -> None:
    """Dispatch the correct trigger method based on trigger type."""
    if trigger_type == "webhook":
        webhook_path = extract_webhook_path(workflow_json)
        await client.trigger_webhook(webhook_path, payload={"test": True})
    else:
        await client.run_workflow(workflow_id)


async def _safe_deactivate(client: N8nClient, workflow_id: str) -> None:
    """Deactivate workflow, swallowing errors."""
    try:
        await client.deactivate_workflow(workflow_id)
    except Exception:
        pass


def _error_result(error_msg: str, *, node_name: str = "unknown") -> dict:
    """Build a failure return dict from a caught exception."""
    return {
        "execution_result": ExecutionResult(
            status="error", execution_id="", data=None,
            error={"type": None, "node_name": node_name,
                   "message": error_msg, "description": None,
                   "line_number": None, "stack": None},
        ),
        "status": "fixing",
        "messages": [HumanMessage(content=f"[Test] Error ({node_name}): {error_msg}")],
    }


def _parse_execution(execution: dict) -> ExecutionResult:
    """Parse raw n8n execution into ExecutionResult."""
    status = execution.get("status", "error")
    error = None
    if status == "error":
        run_data = execution.get("data", {}).get("resultData", {}).get("runData", {})
        error = _extract_error_from_rundata(run_data)

    return ExecutionResult(
        status=status,
        execution_id=execution.get("id", ""),
        data=execution.get("data"),
        error=error,
    )


def _extract_error_from_rundata(run_data: dict) -> dict | None:
    """Find the failing node in runData and extract raw error info."""
    for node_name, entries in run_data.items():
        for entry in entries:
            if entry.get("executionStatus") == "error":
                err = entry.get("error", {})
                return {
                    "type": None,
                    "node_name": node_name,
                    "message": err.get("message", "Unknown error"),
                    "description": err.get("description"),
                    "line_number": err.get("lineNumber"),
                    "stack": err.get("stack"),
                }
    return None
