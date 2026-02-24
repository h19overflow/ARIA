"""Chat tab component for the ARIA Dev Console."""
from __future__ import annotations

from typing import TYPE_CHECKING, Callable

import streamlit as st

from src.streamlit_app.design_tokens import TOKENS

if TYPE_CHECKING:
    from src.agentic_system.shared.state import ARIAState
    from src.streamlit_app.state_manager import SessionState


def render_chat_tab(
    session: SessionState,
    on_submit: Callable[[str], None],
    on_resume: Callable[[str], None],
) -> None:
    _render_message_history(session.aria_state)
    st.divider()
    _render_input_area(session, on_submit, on_resume)


def _render_message_history(state: ARIAState) -> None:
    messages = state.get("messages", [])
    for msg in messages:
        role = getattr(msg, "type", "human")
        content = getattr(msg, "content", str(msg))
        _render_bubble(role, content)


def _render_bubble(role: str, content: str) -> None:
    if role == "human":
        st.markdown(
            f'<div style="text-align:right">'
            f'<span style="background:{TOKENS["accent_blue"]};color:#fff;'
            f'padding:8px 14px;border-radius:14px 14px 2px 14px;display:inline-block;'
            f'max-width:80%;margin:4px 0">{content}</span></div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f'<div style="background:{TOKENS["bg_surface"]};padding:10px 14px;'
            f'border-radius:2px 14px 14px 14px;margin:4px 0;max-width:80%">'
            f'<small style="color:{TOKENS["text_muted"]}">[Orchestrator]</small><br>'
            f'{content}</div>',
            unsafe_allow_html=True,
        )


def _render_input_area(
    session: SessionState,
    on_submit: Callable[[str], None],
    on_resume: Callable[[str], None],
) -> None:
    phase = session.app_phase
    interrupt_type = session.interrupt_type

    if phase == "idle":
        _render_idle_input(on_submit)
    elif phase == "preflight" and not session.at_interrupt:
        st.spinner("Orchestrator thinking...")
    elif session.at_interrupt and interrupt_type == "clarify":
        _render_clarify_input(session.aria_state, on_resume)
    elif session.at_interrupt and interrupt_type == "credential":
        _render_credential_banner(on_resume)
    elif phase == "preflight" and not session.at_interrupt:
        _render_preflight_done_banner()
    elif phase == "build_cycle" and not session.at_interrupt:
        st.info("Build cycle running — input disabled.")
    elif session.at_interrupt and interrupt_type == "hitl_escalation":
        _render_escalation_banner(on_resume)
    elif phase == "done":
        _render_preflight_done_banner()


def _render_idle_input(on_submit: Callable[[str], None]) -> None:
    prompt = st.text_area(
        "Describe the workflow you want to build...",
        key="idle_input",
        height=100,
    )
    if st.button("Submit", key="btn_submit_idle") and prompt:
        on_submit(prompt)


def _render_clarify_input(state: ARIAState, on_resume: Callable[[str], None]) -> None:
    question = state.get("pending_question", "Please clarify:")
    st.warning(f"**Clarification needed:** {question}")
    reply = st.text_input("Your reply", key="clarify_reply")
    if st.button("Send reply", key="btn_clarify") and reply:
        on_resume(reply)


def _render_credential_banner(on_resume: Callable[[str], None]) -> None:
    st.warning("Credential collection required. Check credentials, then resume.")
    if st.button("Resume after credentials", key="btn_resume_cred"):
        on_resume("credentials_provided")


def _render_preflight_done_banner() -> None:
    st.success("Preflight complete. Click **Start Build** in the sidebar.")


def _render_escalation_banner(on_resume: Callable[[str], None]) -> None:
    st.error("Build escalated — fix budget exhausted. Choose an action:")
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("🔧 Manual Fix", key="btn_manual_fix"):
            on_resume("manual_fix")
    with col2:
        if st.button("🔄 Replan", key="btn_replan"):
            on_resume("replan")
    with col3:
        if st.button("✖ Abort", key="btn_abort"):
            on_resume("abort")
