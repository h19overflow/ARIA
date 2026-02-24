"""Phases tab component for the ARIA Dev Console."""
from __future__ import annotations

import json
from typing import TYPE_CHECKING

import streamlit as st

if TYPE_CHECKING:
    from src.agentic_system.shared.state import ARIAState, PhaseEntry


def render_phases_tab(state: ARIAState) -> None:
    build_phase = state.get("build_phase", 0)
    total_phases = state.get("total_phases", 0)
    phase_map: list[PhaseEntry] = state.get("phase_node_map", [])

    if not total_phases:
        st.info("No phases planned yet.")
        return

    progress = build_phase / total_phases if total_phases else 0
    st.progress(progress, text=f"Phase {build_phase} / {total_phases}")

    for idx, phase in enumerate(phase_map):
        _render_phase_expander(idx, phase, build_phase, state)


def _render_phase_expander(
    idx: int,
    phase: PhaseEntry,
    current_phase: int,
    state: ARIAState,
) -> None:
    is_current = idx == current_phase
    label = f"Phase {idx + 1}" + (" — current" if is_current else "")

    with st.expander(label, expanded=is_current):
        _render_nodes_list(phase.get("nodes", []))
        _render_entry_edges(phase.get("entry_edges", []))
        _render_engineer_output(state, idx)
        _render_deploy_status(state, idx)
        _render_test_result(state, idx)
        _render_debugger_output(state, idx)


def _render_nodes_list(nodes: list[str]) -> None:
    if nodes:
        st.markdown("**Nodes:** " + ", ".join(f"`{n}`" for n in nodes))


def _render_entry_edges(edges: list) -> None:
    if not edges:
        return
    st.markdown("**Entry edges:**")
    for e in edges:
        branch = f" ({e.get('branch')})" if e.get("branch") else ""
        st.caption(f"  {e.get('from_node')} → {e.get('to_node')}{branch}")


def _render_engineer_output(state: ARIAState, idx: int) -> None:
    templates = state.get("node_templates", [])
    if not templates:
        return
    phase_templates = [t for t in templates if t.get("phase_index") == idx]
    if not phase_templates:
        return
    with st.expander("Engineer output (JSON)", expanded=False):
        st.json(phase_templates)


def _render_deploy_status(state: ARIAState, idx: int) -> None:
    if state.get("n8n_workflow_id") and idx == state.get("build_phase", 0):
        st.success(f"Deployed: `{state['n8n_workflow_id']}`")


def _render_test_result(state: ARIAState, idx: int) -> None:
    result = state.get("execution_result")
    if result and idx == state.get("build_phase", 0):
        status = result.get("status", "unknown")
        if status == "success":
            st.success(f"Test passed (exec: {result.get('execution_id')})")
        else:
            err = result.get("error") or {}
            st.error(f"Test failed: {err.get('message', 'unknown error')}")


def _render_debugger_output(state: ARIAState, idx: int) -> None:
    classified = state.get("classified_error")
    if classified and state.get("fix_attempts", 0) > 0:
        if idx == state.get("build_phase", 0):
            st.warning(f"Debugging: {classified.get('type')} — {classified.get('message')}")
