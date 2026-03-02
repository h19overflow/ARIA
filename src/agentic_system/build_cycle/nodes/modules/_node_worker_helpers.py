"""Helper functions for node_worker_node — validation, parsing, and result construction."""
from __future__ import annotations

import json
import logging
import re

from langchain_core.messages import AIMessage

log = logging.getLogger("aria.node_worker")


def extract_parameters_from_response(ai_message: AIMessage, node_spec: dict) -> dict:
    """Parse parameters dict from the LLM's text response, falling back to hints."""
    raw_text = _get_message_text(ai_message)
    parsed = _parse_json_from_text(raw_text)

    if isinstance(parsed, dict) and parsed.get("parameters"):
        return parsed["parameters"]
    if isinstance(parsed, dict) and parsed:
        return parsed

    log.warning("[NodeWorker] Could not parse parameters, using parameter_hints")
    return node_spec.get("parameter_hints", {})


def _get_message_text(ai_message: AIMessage) -> str:
    """Extract text content from an AIMessage (handles Gemini's list format)."""
    content = ai_message.content
    if isinstance(content, list):
        return "".join(
            block.get("text", "") if isinstance(block, dict) else str(block)
            for block in content
        )
    return str(content)


def _parse_json_from_text(text: str) -> dict | None:
    """Extract a JSON object from text, handling markdown code fences."""
    fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fence_match:
        try:
            return json.loads(fence_match.group(1))
        except json.JSONDecodeError:
            pass

    brace_start = text.find("{")
    if brace_start >= 0:
        try:
            return json.loads(text[brace_start:])
        except json.JSONDecodeError:
            pass

    return None


def _validate_node_output(node_json: dict) -> list[str]:
    """Validate the built node has required fields. Returns list of error strings."""
    errors = []
    params = node_json.get("parameters", {})
    node_type = node_json.get("type", "").lower()

    if not params:
        errors.append(f"Empty parameters for node '{node_json.get('name', '?')}' ({node_type})")

    if "webhook" in node_type and "path" not in params:
        errors.append(f"Webhook node '{node_json.get('name', '?')}' missing required 'path' parameter")

    return errors


def _success_result(node_name: str, node_json: dict) -> dict:
    """Build a passing NodeResult."""
    return {
        "node_name": node_name,
        "node_json": node_json,
        "validation_passed": True,
        "validation_errors": [],
    }


def _failure_result(node_name: str, errors: Exception | list[str]) -> dict:
    """Build a failing NodeResult from an exception or error list."""
    if isinstance(errors, list):
        error_strings = errors
    else:
        error_strings = [f"{type(errors).__name__}: {errors}"]
    return {
        "node_name": node_name,
        "node_json": {},
        "validation_passed": False,
        "validation_errors": error_strings,
    }
