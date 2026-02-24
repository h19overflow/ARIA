"""Raw state tab component for the ARIA Dev Console."""
from __future__ import annotations

from typing import TYPE_CHECKING

import streamlit as st

if TYPE_CHECKING:
    from src.agentic_system.shared.state import ARIAState

_NOISY_FIELDS = ["messages", "node_templates"]
_ALL_FIELDS = [
    "intent", "required_nodes", "resolved_credential_ids", "pending_credential_types",
    "build_blueprint", "orchestrator_decision", "pending_question", "orchestrator_turns",
    "node_templates", "workflow_json", "n8n_workflow_id", "n8n_execution_id",
    "execution_result", "classified_error", "fix_attempts", "webhook_url",
    "status", "build_phase", "total_phases", "phase_node_map", "messages",
]


def render_raw_state_tab(state: ARIAState, prev_state: ARIAState | None) -> None:
    col1, col2 = st.columns([3, 1])
    with col1:
        hidden = st.multiselect(
            "Hide fields",
            options=_ALL_FIELDS,
            default=_NOISY_FIELDS,
            key="raw_state_hidden",
        )
    with col2:
        show_diff = st.toggle("Diff view", value=False, key="raw_state_diff")

    filtered = _filter_state(state, hidden)

    if show_diff and prev_state is not None:
        _render_diff(filtered, _filter_state(prev_state, hidden))
    else:
        st.json(filtered)


def _filter_state(state: ARIAState, hidden: list[str]) -> dict:
    return {k: v for k, v in dict(state).items() if k not in hidden}


def _render_diff(current: dict, previous: dict) -> None:
    changed_keys = {k for k in current if current.get(k) != previous.get(k)}
    added_keys = set(current) - set(previous)

    st.markdown("**Changed fields highlighted:**")
    for key, value in current.items():
        if key in added_keys:
            _render_highlighted_field(key, value, "#22c55e22")
        elif key in changed_keys:
            _render_highlighted_field(key, value, "#f59e0b22")
        else:
            with st.expander(f"`{key}`", expanded=False):
                st.json({key: value})


def _render_highlighted_field(key: str, value: object, bg: str) -> None:
    st.markdown(
        f'<div style="background:{bg};border-radius:6px;padding:4px 8px;margin:2px 0">'
        f'<b>{key}</b></div>',
        unsafe_allow_html=True,
    )
    st.json({key: value})
