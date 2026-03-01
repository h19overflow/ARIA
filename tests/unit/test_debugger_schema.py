"""Tests for expanded DebuggerOutput schema."""
import pytest
from src.agentic_system.build_cycle.schemas.execution import (
    DebuggerOutput,
    FixedNode,
    NewNode,
)


def test_fixed_node_minimal():
    node = FixedNode(node_name="Gmail", parameters={"to": "a@b.com"})
    assert node.node_name == "Gmail"
    assert node.new_type is None
    assert node.credentials is None


def test_fixed_node_with_type_change():
    node = FixedNode(
        node_name="LangChain Agent",
        parameters={"url": "https://api.openai.com/v1/chat"},
        new_type="n8n-nodes-base.httpRequest",
    )
    assert node.new_type == "n8n-nodes-base.httpRequest"


def test_new_node_full():
    node = NewNode(
        name="Transform Data",
        type="n8n-nodes-base.code",
        parameters={"jsCode": "return items;"},
        position=[400, 200],
    )
    assert node.name == "Transform Data"
    assert node.position == [400, 200]
    assert node.credentials is None


def test_debugger_output_with_full_fix():
    output = DebuggerOutput(
        error_type="schema",
        node_name="Gmail",
        message="Missing 'to' field",
        fixed_nodes=[FixedNode(node_name="Gmail", parameters={"to": "a@b.com"})],
        fixed_connections={"Gmail": {"main": [[{"node": "End", "type": "main", "index": 0}]]}},
    )
    assert len(output.fixed_nodes) == 1
    assert output.fixed_connections is not None
    assert output.added_nodes is None
    assert output.removed_node_names is None


def test_debugger_output_with_node_substitution():
    output = DebuggerOutput(
        error_type="missing_node",
        node_name="LangChain Agent",
        message="Node type not installed",
        fixed_nodes=[FixedNode(
            node_name="LangChain Agent",
            parameters={"url": "https://api.openai.com/v1/chat"},
            new_type="n8n-nodes-base.httpRequest",
        )],
    )
    assert output.fixed_nodes[0].new_type == "n8n-nodes-base.httpRequest"


def test_debugger_output_with_added_and_removed_nodes():
    output = DebuggerOutput(
        error_type="logic",
        node_name="HTTP Request",
        message="Need transform step between nodes",
        added_nodes=[NewNode(
            name="Transform",
            type="n8n-nodes-base.code",
            parameters={"jsCode": "return items;"},
            position=[300, 200],
        )],
        removed_node_names=["Old Transform"],
        fixed_connections={"Trigger": {"main": [[{"node": "Transform", "type": "main", "index": 0}]]}},
    )
    assert len(output.added_nodes) == 1
    assert output.removed_node_names == ["Old Transform"]


def test_debugger_output_unfixable():
    output = DebuggerOutput(
        error_type="auth",
        node_name="Gmail",
        message="Invalid credentials",
    )
    assert output.fixed_nodes is None
    assert output.fixed_connections is None
    assert output.added_nodes is None
    assert output.removed_node_names is None


def test_debugger_output_backward_compat_no_fix():
    """Ensure unfixable errors still work with all None fix fields."""
    output = DebuggerOutput(
        error_type="rate_limit",
        node_name="OpenAI",
        message="429 Too Many Requests",
    )
    assert output.fixed_nodes is None
