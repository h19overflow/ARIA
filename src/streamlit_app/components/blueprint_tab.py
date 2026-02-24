"""Blueprint tab component for the ARIA Dev Console."""
from __future__ import annotations

from typing import TYPE_CHECKING

import streamlit as st

if TYPE_CHECKING:
    from src.agentic_system.shared.state import BuildBlueprint, WorkflowTopology


def render_blueprint_tab(blueprint: BuildBlueprint | None) -> None:
    if blueprint is None:
        st.info("No blueprint yet. Complete preflight to generate one.")
        return

    _render_header_row(blueprint)
    st.divider()
    _render_topology(blueprint.get("topology"))
    st.divider()
    _render_required_nodes(blueprint.get("required_nodes", []))


def _render_header_row(blueprint: BuildBlueprint) -> None:
    left, right = st.columns([2, 1])
    with left:
        st.info(f"**Intent:** {blueprint.get('user_description', blueprint.get('intent', ''))}")
    with right:
        creds = blueprint.get("credential_ids", {})
        if creds:
            st.markdown("**Credentials**")
            rows = [{"Service": k, "ID": v} for k, v in creds.items()]
            st.table(rows)
        else:
            st.caption("No credentials required.")


def _render_topology(topology: WorkflowTopology | None) -> None:
    if not topology:
        st.caption("No topology data.")
        return
    st.subheader("Workflow topology")
    dot = _topology_to_dot(topology)
    st.graphviz_chart(dot)


def _topology_to_dot(topology: WorkflowTopology) -> str:
    """Convert WorkflowTopology to a Graphviz DOT string."""
    lines: list[str] = ["digraph G {", "  rankdir=LR;", "  node [style=filled, fontname=Helvetica];"]
    entry = topology.get("entry_node", "")
    branch_nodes = set(topology.get("branch_nodes", []))

    for node in topology.get("nodes", []):
        shape = "diamond" if node in branch_nodes else "box"
        border = "2" if node == entry else "1"
        lines.append(f'  "{node}" [shape={shape}, penwidth={border}];')

    for edge in topology.get("edges", []):
        src = edge.get("from_node", "")
        dst = edge.get("to_node", "")
        label = edge.get("branch") or ""
        label_attr = f' [label="{label}"]' if label else ""
        lines.append(f'  "{src}" -> "{dst}"{label_attr};')

    lines.append("}")
    return "\n".join(lines)


def _render_required_nodes(nodes: list[str]) -> None:
    if not nodes:
        return
    with st.expander("Required nodes", expanded=False):
        for node in nodes:
            st.markdown(
                f'<span style="font-family:monospace;background:#1a1d27;'
                f'padding:2px 8px;border-radius:6px;margin:2px;display:inline-block">'
                f'{node}</span>',
                unsafe_allow_html=True,
            )
