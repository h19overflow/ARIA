"""Async bridge between Streamlit (sync) and ARIAPipeline (async)."""
from __future__ import annotations

import asyncio
import time
import threading
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from src.streamlit_app.state_manager import LogEntry

if TYPE_CHECKING:
    from src.agentic_system.graph import ARIAPipeline
    from src.agentic_system.shared.state import ARIAState


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def _run_async(coro: object) -> object:
    """Run an async coroutine in a fresh thread with its own event loop.

    This avoids event-loop conflicts with Streamlit's internal loop.
    """
    result_box: list = []
    error_box: list = []

    def _target() -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result_box.append(loop.run_until_complete(coro))
        except Exception as exc:  # noqa: BLE001
            error_box.append(exc)
        finally:
            loop.close()

    t = threading.Thread(target=_target, daemon=True)
    t.start()
    t.join()

    if error_box:
        raise error_box[0]
    return result_box[0]


_NODE_LABELS: dict[str, str] = {
    "rag_retriever": "Retrieving node templates from ChromaDB...",
    "phase_planner": "Planning build phases...",
    "engineer": "Engineering workflow JSON...",
    "deploy": "Deploying to n8n...",
    "test": "Testing workflow...",
    "debugger": "Debugging error...",
    "activate": "Activating workflow...",
    "hitl_fix_escalation": "Escalating to user...",
    "advance_phase": "Advancing to next phase...",
    "fail": "Build failed.",
}


def _node_progress_label(node_name: str, update: dict) -> str:
    """Return a human-readable progress label for a node update."""
    base = _NODE_LABELS.get(node_name, f"Running {node_name}...")
    phase = update.get("build_phase")
    total = update.get("total_phases")
    if node_name == "engineer" and phase is not None and total:
        return f"Engineering phase {phase + 1}/{total}..."
    return base


class PipelineRunner:
    """Async bridge between Streamlit (sync) and ARIAPipeline (async)."""

    def __init__(self, pipeline: ARIAPipeline, log_sink: list[LogEntry]) -> None:
        self._pipeline = pipeline
        self._logs = log_sink

    def run_preflight(self, state: ARIAState, config: dict) -> ARIAState:
        start = time.monotonic()
        self._log("runner", "INFO", "Starting preflight")
        result = _run_async(self._pipeline.run_preflight(state, config))
        ms = int((time.monotonic() - start) * 1000)
        self._log("runner", "INFO", f"Preflight complete in {ms}ms", duration_ms=ms)
        return result

    def resume_preflight(self, answer: object, config: dict) -> ARIAState:
        preview = str(answer)[:60]
        self._log("runner", "INFO", f"Resuming preflight: {preview!r}")
        return _run_async(self._pipeline.resume_preflight(answer, config))

    def run_build_cycle(
        self,
        state: ARIAState,
        config: dict,
        progress_sink: list[str] | None = None,
    ) -> ARIAState:
        """Run build cycle, optionally collecting per-node progress labels."""
        start = time.monotonic()
        self._log("runner", "INFO", "Starting build cycle")

        def _on_node(node_name: str, update: dict) -> None:
            label = _node_progress_label(node_name, update)
            self._log(node_name, "INFO", label)
            if progress_sink is not None:
                progress_sink.append(label)

        result = _run_async(self._pipeline.stream_build_cycle(state, config, _on_node))
        ms = int((time.monotonic() - start) * 1000)
        self._log("runner", "INFO", f"Build cycle complete in {ms}ms", duration_ms=ms)
        return result

    def resume_build_cycle(self, answer: object, config: dict) -> ARIAState:
        preview = str(answer)[:60]
        self._log("runner", "INFO", f"Resuming build cycle: {preview!r}")
        return _run_async(self._pipeline.resume_build_cycle(answer, config))

    def _capture_logs(self, node_name: str, event: dict) -> None:
        usage = event.get("token_usage")
        self._log(node_name, "LLM", str(event.get("message", "")), token_usage=usage)

    def _log(
        self,
        node: str,
        level: str,
        message: str,
        token_usage: dict | None = None,
        duration_ms: int | None = None,
    ) -> None:
        self._logs.append(
            LogEntry(
                timestamp=_iso_now(),
                node=node,
                level=level,
                message=message,
                token_usage=token_usage,
                duration_ms=duration_ms,
            )
        )
