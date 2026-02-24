"""Log viewer component for the ARIA Dev Console."""
from __future__ import annotations

import streamlit as st

from src.streamlit_app.design_tokens import TOKENS
from src.streamlit_app.state_manager import LogEntry

_LEVEL_COLORS: dict[str, str] = {
    "INFO":  TOKENS["text_muted"],
    "WARN":  TOKENS["accent_amber"],
    "ERROR": TOKENS["accent_red"],
    "LLM":   TOKENS["accent_purple"],
}

_PROMPT_COST = 0.000003
_COMPLETION_COST = 0.000015


def render_log_viewer(logs: list[LogEntry]) -> None:
    _render_llm_summary(logs)
    st.divider()
    filters = _render_filters(logs)
    filtered = _apply_filters(logs, filters)
    _render_log_table(filtered)


def _render_llm_summary(logs: list[LogEntry]) -> None:
    llm_logs = [l for l in logs if l.level == "LLM" and l.token_usage]
    total_prompt = sum(l.token_usage.get("prompt_tokens", 0) for l in llm_logs)
    total_completion = sum(l.token_usage.get("completion_tokens", 0) for l in llm_logs)
    cost = total_prompt * _PROMPT_COST + total_completion * _COMPLETION_COST

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("LLM calls", len(llm_logs))
    col2.metric("Prompt tokens", f"{total_prompt:,}")
    col3.metric("Completion tokens", f"{total_completion:,}")
    col4.metric("Est. cost", f"${cost:.4f}")


def _render_filters(logs: list[LogEntry]) -> dict:
    all_nodes = sorted({l.node for l in logs})
    all_levels = sorted({l.level for l in logs})
    col1, col2 = st.columns(2)
    with col1:
        nodes = st.multiselect("Filter nodes", all_nodes, default=all_nodes, key="log_nodes")
    with col2:
        levels = st.multiselect("Filter levels", all_levels, default=all_levels, key="log_levels")
    return {"nodes": nodes, "levels": levels}


def _apply_filters(logs: list[LogEntry], filters: dict) -> list[LogEntry]:
    return [
        l for l in logs
        if l.node in filters["nodes"] and l.level in filters["levels"]
    ]


def _render_log_table(logs: list[LogEntry]) -> None:
    if not logs:
        st.caption("No log entries.")
        return

    rows: list[str] = []
    for entry in logs:
        colour = _LEVEL_COLORS.get(entry.level, TOKENS["text_muted"])
        tokens_str = _format_tokens(entry.token_usage)
        dur_str = f" +{entry.duration_ms}ms" if entry.duration_ms else ""
        ts = entry.timestamp[11:23]  # HH:MM:SS.mmm
        row = (
            f'<span style="color:{TOKENS["text_muted"]}">{ts}</span> '
            f'<span style="color:{TOKENS["accent_blue"]}">[{entry.node}]</span> '
            f'<span style="color:{colour}">[{entry.level}]</span> '
            f'{entry.message}{dur_str}{tokens_str}'
        )
        rows.append(row)

    html = "<br>".join(rows)
    st.markdown(
        f'<pre style="font-family:{TOKENS["font_mono"]};font-size:0.75rem;'
        f'background:{TOKENS["bg_code"]};padding:12px;border-radius:8px;'
        f'overflow-x:auto;line-height:1.6">{html}</pre>',
        unsafe_allow_html=True,
    )


def _format_tokens(usage: dict | None) -> str:
    if not usage:
        return ""
    p = usage.get("prompt_tokens", 0)
    c = usage.get("completion_tokens", 0)
    return f' <span style="color:{TOKENS["accent_purple"]}">[p:{p} c:{c}]</span>'
