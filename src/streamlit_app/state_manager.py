"""Type-safe wrapper around st.session_state for the ARIA Dev Console."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal

import streamlit as st

if TYPE_CHECKING:
    from src.agentic_system.shared.state import ARIAState
    from src.streamlit_app.pipeline_runner import PipelineRunner


@dataclass
class LogEntry:
    timestamp: str
    node: str
    level: str  # "INFO" | "WARN" | "ERROR" | "LLM"
    message: str
    token_usage: dict | None = None
    duration_ms: int | None = None


def _empty_aria_state() -> ARIAState:
    from src.agentic_system.shared.state import ARIAState  # noqa: PLC0415
    return ARIAState(
        messages=[],
        intent="",
        required_nodes=[],
        resolved_credential_ids={},
        pending_credential_types=[],
        build_blueprint=None,
        topology=None,
        user_description="",
        orchestrator_decision="",
        pending_question="",
        orchestrator_turns=0,
        node_templates=[],
        workflow_json=None,
        n8n_workflow_id=None,
        n8n_execution_id=None,
        execution_result=None,
        classified_error=None,
        fix_attempts=0,
        webhook_url=None,
        status="planning",
        build_phase=0,
        total_phases=0,
        phase_node_map=[],
    )


AppPhase = Literal["idle", "preflight", "build_cycle", "done"]
InterruptType = Literal["clarify", "credential", "credential_ambiguity", "hitl_escalation"]


class SessionState:
    """Type-safe wrapper around st.session_state."""

    _KEY = "_aria_session"

    @classmethod
    def init(cls) -> "SessionState":
        if cls._KEY not in st.session_state:
            st.session_state[cls._KEY] = cls._build_defaults()
        return cls()

    @staticmethod
    def _build_defaults() -> dict:
        from src.agentic_system.graph import ARIAPipeline  # noqa: PLC0415
        from src.streamlit_app.pipeline_runner import PipelineRunner  # noqa: PLC0415

        logs: list[LogEntry] = []
        pipeline = ARIAPipeline()
        runner = PipelineRunner(pipeline, logs)
        return {
            "aria_state": _empty_aria_state(),
            "pipeline": pipeline,
            "runner": runner,
            "app_phase": "idle",
            "logs": logs,
            "thread_id": str(uuid.uuid4()),
            "at_interrupt": False,
            "interrupt_type": None,
            "prev_state": None,
        }

    def _s(self) -> dict:
        return st.session_state[self._KEY]

    # --- Properties ---
    @property
    def aria_state(self) -> ARIAState:
        return self._s()["aria_state"]

    @aria_state.setter
    def aria_state(self, v: ARIAState) -> None:
        self._s()["aria_state"] = v

    @property
    def pipeline(self) -> ARIAPipeline:
        return self._s()["pipeline"]

    @property
    def runner(self) -> PipelineRunner:
        return self._s()["runner"]

    @property
    def app_phase(self) -> AppPhase:
        return self._s()["app_phase"]

    @app_phase.setter
    def app_phase(self, v: AppPhase) -> None:
        self._s()["app_phase"] = v

    @property
    def logs(self) -> list[LogEntry]:
        return self._s()["logs"]

    @property
    def thread_id(self) -> str:
        return self._s()["thread_id"]

    @property
    def at_interrupt(self) -> bool:
        return self._s()["at_interrupt"]

    @at_interrupt.setter
    def at_interrupt(self, v: bool) -> None:
        self._s()["at_interrupt"] = v

    @property
    def interrupt_type(self) -> InterruptType | None:
        return self._s()["interrupt_type"]

    @interrupt_type.setter
    def interrupt_type(self, v: InterruptType | None) -> None:
        self._s()["interrupt_type"] = v

    @property
    def prev_state(self) -> ARIAState | None:
        return self._s()["prev_state"]

    def update_from_result(self, result: ARIAState) -> None:
        """Merge result into aria_state, snapshot prev_state."""
        self._s()["prev_state"] = dict(self.aria_state)
        self._s()["aria_state"] = result
