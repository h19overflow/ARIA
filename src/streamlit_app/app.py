"""ARIA Dev Console — Streamlit entry point."""
from __future__ import annotations

import uuid

import streamlit as st

from src.streamlit_app.state_manager import SessionState
from src.streamlit_app.components.sidebar import render_sidebar
from src.streamlit_app.components.chat_tab import render_chat_tab
from src.streamlit_app.components.blueprint_tab import render_blueprint_tab
from src.streamlit_app.components.phases_tab import render_phases_tab
from src.streamlit_app.components.raw_state_tab import render_raw_state_tab
from src.streamlit_app.components.log_viewer import render_log_viewer

st.set_page_config(
    page_title="ARIA Dev Console",
    page_icon="🔮",
    layout="wide",
    initial_sidebar_state="expanded",
)


def _config(session: SessionState) -> dict:
    return {"configurable": {"thread_id": session.thread_id}}


def _handle_submit(prompt: str, session: SessionState) -> None:
    session.aria_state = {**session.aria_state, "messages": [("human", prompt)]}
    session.app_phase = "preflight"
    try:
        result = session.runner.run_preflight(session.aria_state, _config(session))
        session.update_from_result(result)
        _detect_interrupt(session, "preflight")
    except Exception as exc:  # noqa: BLE001
        st.error(f"Preflight error: {exc}")


def _handle_resume(answer: str, session: SessionState) -> None:
    phase = session.app_phase
    interrupt_type = session.interrupt_type
    # Credential resumes pass {} so saver skips saving; user already did it in n8n.
    resume_value: object = {} if interrupt_type == "credential" else answer
    try:
        if phase == "preflight":
            result = session.runner.resume_preflight(resume_value, _config(session))
        else:
            result = session.runner.resume_build_cycle(resume_value, _config(session))
        session.update_from_result(result)
        session.at_interrupt = False
        session.interrupt_type = None
        _detect_interrupt(session, phase)
    except Exception as exc:  # noqa: BLE001
        st.error(f"Resume error: {exc}")


def _detect_interrupt(session: SessionState, phase: str) -> None:
    state = session.aria_state
    decision = state.get("orchestrator_decision", "")
    pending_creds = state.get("pending_credential_types", [])
    status = state.get("status", "")
    has_interrupt = bool(state.get("__interrupt__"))

    if decision == "clarify" and phase == "preflight" and has_interrupt:
        session.at_interrupt = True
        session.interrupt_type = "clarify"
    elif pending_creds and phase == "preflight" and has_interrupt:
        session.at_interrupt = True
        session.interrupt_type = "credential"
    elif phase == "build_cycle" and has_interrupt:
        # HITL escalation fires when fix budget is exhausted (status="fixing")
        session.at_interrupt = True
        session.interrupt_type = "hitl_escalation"
    elif phase == "preflight" and not has_interrupt and state.get("build_blueprint"):
        # Preflight finished cleanly — ready to start build
        session.at_interrupt = False
        session.interrupt_type = None
    elif status in ("done", "failed"):
        session.app_phase = "done"
        session.at_interrupt = False


def _handle_start_build(session: SessionState) -> None:
    session.app_phase = "build_cycle"
    try:
        result = session.runner.run_build_cycle(session.aria_state, _config(session))
        session.update_from_result(result)
        _detect_interrupt(session, "build_cycle")
    except Exception as exc:  # noqa: BLE001
        st.error(f"Build cycle error: {exc}")


def _handle_reset(session: SessionState) -> None:
    del st.session_state["_aria_session"]
    st.rerun()


def main() -> None:
    session = SessionState.init()

    # Wire sidebar buttons
    if st.session_state.get("btn_reset"):
        _handle_reset(session)
        return
    if st.session_state.get("btn_start") and session.app_phase == "preflight":
        _handle_start_build(session)

    render_sidebar(session.aria_state, session.app_phase)

    chat_tab, blueprint_tab, phases_tab, state_tab, logs_tab = st.tabs(
        ["💬 Chat", "🗺 Blueprint", "⚙ Phases", "🧾 State", "📋 Logs"]
    )

    with chat_tab:
        render_chat_tab(
            session,
            on_submit=lambda p: _handle_submit(p, session),
            on_resume=lambda a: _handle_resume(a, session),
        )

    with blueprint_tab:
        render_blueprint_tab(session.aria_state.get("build_blueprint"))

    with phases_tab:
        render_phases_tab(session.aria_state)

    with state_tab:
        render_raw_state_tab(session.aria_state, session.prev_state)

    with logs_tab:
        render_log_viewer(session.logs)


main()
