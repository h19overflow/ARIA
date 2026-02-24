"""Build Cycle Test — activate, trigger webhook, poll, deactivate on failure."""
from __future__ import annotations

from langchain_core.messages import HumanMessage

from src.agentic_system.shared.state import ARIAState, ExecutionResult
from src.boundary.n8n.client import N8nClient


async def test_node(state: ARIAState) -> dict:
    """Activate workflow, fire webhook, poll result, deactivate on failure."""
    workflow_id = state["n8n_workflow_id"]
    workflow_json = state["workflow_json"]
    webhook_path = _extract_webhook_path(workflow_json)

    client = N8nClient()
    await client.connect()
    try:
        await client.activate_workflow(workflow_id)
        await client.trigger_webhook(webhook_path, payload={"test": True})
        execution = await client.poll_execution(workflow_id, timeout=30.0)
        exec_result = _parse_execution(execution)
        if exec_result["status"] != "success":
            await _safe_deactivate(client, workflow_id)
    except Exception as e:
        await _safe_deactivate(client, workflow_id)
        return _error_result(str(e))
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


async def _safe_deactivate(client: N8nClient, workflow_id: str) -> None:
    """Deactivate workflow, swallowing errors."""
    try:
        await client.deactivate_workflow(workflow_id)
    except Exception:
        pass


def _error_result(error_msg: str) -> dict:
    """Build a failure return dict from a caught exception.

    Error type is left as None so the Debugger agent classifies it from
    the raw message rather than inheriting a hardcoded assumption.
    """
    return {
        "execution_result": ExecutionResult(
            status="error", execution_id="", data=None,
            error={"type": None, "node_name": "unknown",
                   "message": error_msg, "description": None,
                   "line_number": None, "stack": None},
        ),
        "status": "fixing",
        "messages": [HumanMessage(content=f"[Test] Error: {error_msg}")],
    }


def _extract_webhook_path(workflow_json: dict) -> str:
    """Find the webhook path from workflow nodes."""
    for node in workflow_json.get("nodes", []):
        if "webhook" in node.get("type", "").lower():
            return node.get("parameters", {}).get("path", "test-webhook")
    return "test-webhook"


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
    """Find the failing node in runData and extract raw error info.

    Type is intentionally left as None — the Debugger agent classifies it
    from the message and stack so routing reflects the actual error category.
    """
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
