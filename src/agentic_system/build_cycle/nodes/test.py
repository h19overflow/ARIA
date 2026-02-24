"""Build Cycle Test — trigger webhook and poll execution result."""
from __future__ import annotations

from langchain_core.messages import HumanMessage

from src.agentic_system.shared.state import ARIAState, ExecutionResult
from src.boundary.n8n.client import N8nClient


async def test_node(state: ARIAState) -> dict:
    """Fire webhook trigger, poll until execution completes."""
    workflow_id = state["n8n_workflow_id"]
    workflow_json = state["workflow_json"]
    webhook_path = _extract_webhook_path(workflow_json)

    client = N8nClient()
    await client.connect()
    try:
        await client.trigger_webhook(webhook_path, payload={"test": True})
        execution = await client.poll_execution(workflow_id, timeout=30.0)
    finally:
        await client.disconnect()

    exec_result = _parse_execution(execution)
    status = "done" if exec_result["status"] == "success" else "fixing"

    return {
        "execution_result": exec_result,
        "n8n_execution_id": execution.get("id", ""),
        "status": status,
        "messages": [HumanMessage(
            content=f"[Test] Execution {exec_result['status']}: {execution.get('id', 'unknown')}"
        )],
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
    """Find the failing node in runData and extract error info."""
    for node_name, entries in run_data.items():
        for entry in entries:
            if entry.get("executionStatus") == "error":
                err = entry.get("error", {})
                return {
                    "type": "schema",
                    "node_name": node_name,
                    "message": err.get("message", "Unknown error"),
                    "description": err.get("description"),
                    "line_number": err.get("lineNumber"),
                    "stack": err.get("stack"),
                }
    return None
