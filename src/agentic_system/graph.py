"""ARIA pipeline — sequential two-phase runner (Preflight → Build Cycle).

Replaces the old nested-subgraph master graph that caused BUG-6:
MemorySaver checkpointer deadlocked when interrupt() fired inside
compiled subgraphs nested inside a parent StateGraph.

The fix: compile each subgraph independently with its own MemorySaver
and execute them sequentially at the service level.  HITL interrupts
work correctly because each graph is a top-level compiled graph.
"""
from __future__ import annotations

from langgraph.checkpoint.memory import MemorySaver

from src.agentic_system.shared.state import ARIAState
from src.agentic_system.preflight.graph import build_preflight_graph
from src.agentic_system.build_cycle.graph import build_build_cycle_graph


class ARIAPipeline:
    """Sequential runner for the two-phase ARIA pipeline.

    Usage
    -----
    pipeline = ARIAPipeline()

    # Phase 1 — Preflight (handles HITL clarify + credential collection)
    config = {"configurable": {"thread_id": "run-123"}}
    state = await pipeline.run_preflight(initial_state, config)

    # Phase 2 — Build Cycle (handles HITL escalation)
    final_state = await pipeline.run_build_cycle(state, config)
    """

    def __init__(self) -> None:
        preflight_ckpt = MemorySaver()
        build_cycle_ckpt = MemorySaver()

        self._preflight = build_preflight_graph().compile(
            checkpointer=preflight_ckpt,
        )
        self._build_cycle = build_build_cycle_graph().compile(
            checkpointer=build_cycle_ckpt,
        )

    async def run_preflight(
        self,
        state: ARIAState,
        config: dict,
    ) -> ARIAState:
        """Run preflight to completion and return the final state."""
        result = await self._preflight.ainvoke(state, config=config)
        return result

    async def run_build_cycle(
        self,
        state: ARIAState,
        config: dict,
    ) -> ARIAState:
        """Run build cycle to completion and return the final state."""
        result = await self._build_cycle.ainvoke(state, config=config)
        return result

    async def resume_preflight(
        self,
        resume_value: object,
        config: dict,
    ) -> ARIAState:
        """Resume a preflight graph that is paused at an interrupt.

        For clarify interrupts: pass the user's answer string.
        For credential interrupts: pass {} (user already set up creds in n8n).
        LangGraph resume uses Command(resume=value) via None input.
        """
        from langgraph.types import Command  # noqa: PLC0415
        result = await self._preflight.ainvoke(
            Command(resume=resume_value),
            config=config,
        )
        return result

    async def resume_build_cycle(
        self,
        resume_value: object,
        config: dict,
    ) -> ARIAState:
        """Resume a build cycle graph that is paused at HITL escalation."""
        from langgraph.types import Command  # noqa: PLC0415
        result = await self._build_cycle.ainvoke(
            Command(resume=resume_value),
            config=config,
        )
        return result
