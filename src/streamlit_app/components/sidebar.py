"""Sidebar component for the ARIA Dev Console."""
from __future__ import annotations

from typing import TYPE_CHECKING

import streamlit as st

from src.streamlit_app.design_tokens import STATUS_COLORS, TOKENS

if TYPE_CHECKING:
    from src.agentic_system.shared.state import ARIAState


def render_sidebar(state: ARIAState, app_phase: str) -> None:
    with st.sidebar:
        st.markdown("## ARIA Dev Console")
        _render_status_badge(state.get("status", "planning"))
        st.caption(f"Phase: **{app_phase}**")
        _render_phase_counter(state, app_phase)
        _render_fix_attempts(state)
        _render_required_nodes(state)
        _render_workflow_link(state)
        st.caption(f"`{state.get('thread_id', '') or 'no thread'}`" if False else "")
        st.divider()
        _render_action_buttons(app_phase, state)


def _render_status_badge(status: str) -> None:
    colour = STATUS_COLORS.get(status, TOKENS["text_muted"])
    st.markdown(
        f'<span style="background:{colour};color:#fff;'
        f'padding:3px 10px;border-radius:12px;font-size:0.8rem">'
        f'{status.upper()}</span>',
        unsafe_allow_html=True,
    )


def _render_phase_counter(state: ARIAState, app_phase: str) -> None:
    if app_phase == "preflight":
        return
    build_phase = state.get("build_phase", 0)
    total_phases = state.get("total_phases", 0)
    if total_phases:
        st.caption(f"Phase {build_phase + 1} of {total_phases}")


def _render_fix_attempts(state: ARIAState) -> None:
    fix_attempts = state.get("fix_attempts", 0)
    colour = TOKENS["accent_amber"] if fix_attempts > 0 else TOKENS["text_muted"]
    st.markdown(
        f'<span style="color:{colour}">Fix attempts: {fix_attempts} / 3</span>',
        unsafe_allow_html=True,
    )


def _render_required_nodes(state: ARIAState) -> None:
    blueprint = state.get("build_blueprint")
    if not blueprint:
        return
    nodes = blueprint.get("required_nodes", [])
    if nodes:
        st.markdown("**Required nodes**")
        for node in nodes:
            st.markdown(f"- `{node}`")


def _render_workflow_link(state: ARIAState) -> None:
    wf_id = state.get("n8n_workflow_id")
    if wf_id:
        url = f"http://localhost:5678/workflow/{wf_id}"
        st.markdown(f"[Open workflow in n8n]({url})")
    thread_id = st.session_state.get("_aria_session", {}).get("thread_id", "")
    if thread_id:
        st.caption(f"Thread: `{thread_id}`")


def _render_action_buttons(app_phase: str, state: ARIAState) -> None:
    at_interrupt = st.session_state.get("_aria_session", {}).get("at_interrupt", False)
    col1, col2 = st.columns(2)
    with col1:
        st.button("▶ Start", key="btn_start", disabled=(app_phase != "idle"))
    with col2:
        st.button("↩ Resume", key="btn_resume", disabled=(not at_interrupt))
    st.button("↺ Reset Session", key="btn_reset", type="secondary", use_container_width=True)
