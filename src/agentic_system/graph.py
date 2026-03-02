"""ARIA pipeline — Build Cycle LangGraph runner.

This module owns the Build Cycle LangGraph subgraph:
planner → workers → assembler → deploy → END.

Build-cycle resume schema
-------------------------
  {"action": "clarify", "value": "<answer>"}
  {"action": "provide", "credentials": {...}}
  {"action": "resume"}
"""
from __future__ import annotations

from langgraph.checkpoint.memory import MemorySaver

from src.agentic_system.shared.state import ARIAState
from src.agentic_system.build_cycle.graph import build_build_cycle_graph


class ARIAPipeline:
    """Runner for the Phase 2 Build Cycle LangGraph graph.

    Usage
    -----
    pipeline = ARIAPipeline()
    config = {"configurable": {"thread_id": "run-123"}}
    final_state = await pipeline.run_build_cycle(state, config)
    """

    def __init__(self) -> None:
        build_cycle_ckpt = MemorySaver()
        self._build_cycle = build_build_cycle_graph().compile(
            checkpointer=build_cycle_ckpt,
        )

    async def run_build_cycle(
        self,
        state: ARIAState,
        config: dict,
    ) -> ARIAState:
        """Run build cycle to completion and return the final state."""
        result = await self._build_cycle.ainvoke(state, config=config)
        return result

    async def resume_build_cycle(
        self,
        resume_value: dict,
        config: dict,
    ) -> ARIAState:
        """Resume a build cycle graph that is paused at an interrupt.

        ``resume_value`` must follow the unified schema — see module docstring.
        """
        from langgraph.types import Command  # noqa: PLC0415
        result = await self._build_cycle.ainvoke(
            Command(resume=resume_value),
            config=config,
        )
        return result

    async def stream_build_cycle(
        self,
        state: ARIAState,
        config: dict,
        on_node: object = None,
    ) -> ARIAState:
        """Stream build cycle updates, calling on_node(node_name, update) per step.

        Returns the final merged state from the checkpointer.
        """
        async for chunk in self._build_cycle.astream(state, config=config):
            for node_name, update in chunk.items():
                if on_node is not None:
                    on_node(node_name, update)
        snapshot = await self._build_cycle.aget_state(config)
        return snapshot.values
