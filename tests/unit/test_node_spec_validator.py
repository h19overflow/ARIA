"""Tests for NodeSpec.parameter_hints string-to-dict coercion."""
import pytest
from src.agentic_system.build_cycle.schemas.node_plan import NodeSpec


def test_parameter_hints_accepts_dict():
    spec = NodeSpec(
        node_name="Test",
        node_type="n8n-nodes-base.code",
        parameter_hints={"jsCode": "return {}"},
        position_index=0,
    )
    assert spec.parameter_hints == {"jsCode": "return {}"}


def test_parameter_hints_coerces_json_string():
    spec = NodeSpec(
        node_name="Test",
        node_type="n8n-nodes-base.code",
        parameter_hints='{"jsCode": "return {}"}',
        position_index=0,
    )
    assert spec.parameter_hints == {"jsCode": "return {}"}


def test_parameter_hints_invalid_string_returns_empty():
    spec = NodeSpec(
        node_name="Test",
        node_type="n8n-nodes-base.code",
        parameter_hints="not valid json",
        position_index=0,
    )
    assert spec.parameter_hints == {}


def test_parameter_hints_json_array_string_returns_empty():
    spec = NodeSpec(
        node_name="Test",
        node_type="n8n-nodes-base.code",
        parameter_hints='[1, 2, 3]',
        position_index=0,
    )
    assert spec.parameter_hints == {}


def test_parameter_hints_defaults_to_empty_dict():
    spec = NodeSpec(
        node_name="Test",
        node_type="n8n-nodes-base.code",
        position_index=0,
    )
    assert spec.parameter_hints == {}
