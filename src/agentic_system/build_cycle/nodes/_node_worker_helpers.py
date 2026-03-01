"""Helper functions for node_worker_node — validation and result construction."""
from __future__ import annotations


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
