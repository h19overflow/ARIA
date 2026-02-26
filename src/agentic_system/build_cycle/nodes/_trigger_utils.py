"""Shared trigger-detection utilities for test and activate nodes."""
from __future__ import annotations

_SCHEDULE_TYPES = {"n8n-nodes-base.scheduletrigger", "n8n-nodes-base.cron"}
_WEBHOOK_TYPES = {"n8n-nodes-base.webhook"}


def detect_trigger_type(workflow_json: dict) -> str:
    """Classify the workflow's entry trigger as 'webhook', 'schedule', or 'other'.

    Inspects the first node whose type matches a known trigger type.
    Returns 'other' if no recognisable trigger node is found.
    """
    for node in workflow_json.get("nodes", []):
        node_type = node.get("type", "").lower()
        if node_type in _WEBHOOK_TYPES or "webhook" in node_type:
            return "webhook"
        if node_type in _SCHEDULE_TYPES or "schedule" in node_type or "cron" in node_type:
            return "schedule"
    return "other"


def extract_webhook_path(workflow_json: dict) -> str:
    """Return the webhook path from the first webhook node, or 'test-webhook'."""
    for node in workflow_json.get("nodes", []):
        if "webhook" in node.get("type", "").lower():
            return node.get("parameters", {}).get("path", "test-webhook")
    return "test-webhook"
