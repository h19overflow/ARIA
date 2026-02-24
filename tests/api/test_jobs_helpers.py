"""Unit tests for jobs router helper functions."""
from __future__ import annotations

import json

import pytest

from src.api.routers.jobs import _is_terminal


# ---------------------------------------------------------------------------
# Positive
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_is_terminal_done():
    """Should return True for type=done."""
    assert _is_terminal(json.dumps({"type": "done"})) is True


@pytest.mark.unit
def test_is_terminal_error():
    """Should return True for type=error."""
    assert _is_terminal(json.dumps({"type": "error"})) is True


@pytest.mark.unit
def test_is_terminal_bytes_input():
    """Should handle bytes input without raising."""
    assert _is_terminal(b'{"type": "done"}') is True


# ---------------------------------------------------------------------------
# Negative
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_is_terminal_node_event():
    """Should return False for non-terminal type."""
    assert _is_terminal(json.dumps({"type": "node"})) is False


@pytest.mark.unit
def test_is_terminal_ping_type():
    """Should return False for type=ping."""
    assert _is_terminal(json.dumps({"type": "ping"})) is False


# ---------------------------------------------------------------------------
# Edge Case
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_is_terminal_invalid_json():
    """Should return False for non-JSON input."""
    assert _is_terminal("not json") is False


@pytest.mark.unit
def test_is_terminal_empty_object():
    """Should return False for JSON object with no type key."""
    assert _is_terminal("{}") is False


@pytest.mark.unit
def test_is_terminal_null_type():
    """Should return False when type is null."""
    assert _is_terminal(json.dumps({"type": None})) is False
