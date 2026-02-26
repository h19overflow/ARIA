"""ARIA Phase 1 -- Preflight conversational agent."""
from __future__ import annotations

import asyncio
import logging
from typing import Any, AsyncGenerator, Dict, List

from src.agentic_system.shared.base_agent import BaseAgent
from src.agentic_system.shared.node_credential_map import NODE_CREDENTIAL_MAP
from src.agentic_system.conversation.message_builders import build_lc_messages
from .event_handlers import (
    capture_ai_message,
    capture_tool_message,
    extract_result_string,
    handle_tool_end_state,
)
from .prompts import PHASE_1_SYSTEM_PROMPT
from .state import PreflightNotes, PreflightState, get_preflight_state, save_preflight_state
from .tools import commit_preflight, save_credential, scan_credentials

logger = logging.getLogger(__name__)


class PreflightAgent(BaseAgent):
    """Phase 1 Preflight Agent -- credential gathering and saving."""

    def __init__(self, name: str = "PreflightAgent"):
        super().__init__(
            tools=[scan_credentials, save_credential, commit_preflight],
            prompt=PHASE_1_SYSTEM_PROMPT,
            name=name,
            model_name="gemini-3-flash-preview",
        )

    async def initialize_preflight(
        self,
        preflight_id: str,
        conversation_id: str,
        conversation_notes: dict,
    ) -> None:
        """Create PreflightState in Redis with injected Phase 0 context."""
        required_nodes = conversation_notes.get("required_nodes", [])
        required_integrations = conversation_notes.get("required_integrations", [])
        intent_summary = conversation_notes.get("summary", "")

        # Derive credential types from integrations when node types are unavailable
        if not required_nodes and required_integrations:
            required_nodes = _integrations_to_node_keys(required_integrations)

        notes = PreflightNotes(
            required_nodes=required_nodes,
            required_integrations=required_integrations,
        )
        context_message = _build_context_message(intent_summary, required_integrations, required_nodes)

        state = PreflightState(
            preflight_id=preflight_id,
            conversation_id=conversation_id,
            messages=[{"role": "user", "content": context_message}],
            notes=notes,
            committed=False,
        )
        await save_preflight_state(state)

    async def process_message(
        self, preflight_id: str, user_message: str
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Process a user message, stream tokens, execute tools, save state."""
        state = await self._load_or_fail(preflight_id)
        state.messages.append({"role": "user", "content": user_message})
        lc_messages = build_lc_messages(state.messages)

        try:
            current_tool_calls: List[Dict[str, Any]] = []
            async for event in self.stream_events(lc_messages):
                async for sse in self._dispatch_event(event, state, current_tool_calls):
                    yield sse
        except asyncio.CancelledError:
            logger.info("Stream cancelled for preflight %s", preflight_id)
            raise
        except Exception as e:
            logger.error("Error in preflight agent: %s", e, exc_info=True)
            yield {"type": "error", "content": str(e)}
        finally:
            await save_preflight_state(state)

    # -- Private helpers -------------------------------------------------

    async def _load_or_fail(self, preflight_id: str) -> PreflightState:
        """Load existing state or raise ValueError."""
        state = await get_preflight_state(preflight_id)
        if not state:
            raise ValueError(f"Preflight session not found: {preflight_id}")
        return state

    async def _dispatch_event(
        self,
        event: Dict[str, Any],
        state: PreflightState,
        current_tool_calls: List[Dict[str, Any]],
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Route a single stream event to the appropriate handler."""
        token = self._extract_token_text(event)
        if token:
            yield {"type": "token", "content": token}

        tool_start_info = self.tool_start(event)
        if tool_start_info:
            tool_name, tool_args = tool_start_info
            current_tool_calls.append({"name": tool_name, "args": tool_args})
            yield {"type": "tool_start", "tool": tool_name, "args": tool_args}

        tool_end_info = self.tool_end(event)
        if tool_end_info:
            tool_name, tool_result = tool_end_info
            result_str = extract_result_string(tool_result)
            yield {"type": "tool_end", "tool": tool_name, "result": result_str}
            async for sse in handle_tool_end_state(state, tool_name, tool_result, current_tool_calls):
                yield sse

        capture_ai_message(event, state)
        capture_tool_message(event, state)

    def _extract_token_text(self, event: Dict[str, Any]) -> str | None:
        """Extract and normalize a text token from a stream event."""
        token = self.token_delta(event)
        if not token:
            return None
        if isinstance(token, list):
            text = "".join(
                block.get("text", "") if isinstance(block, dict) else str(block)
                for block in token
            )
            return text or None
        return str(token)


def _integrations_to_node_keys(integrations: List[str]) -> List[str]:
    """Map service names (e.g. 'Telegram') to n8n node keys (e.g. 'telegram')."""
    # Build a case-insensitive reverse lookup: display name → node key
    lookup = {k.lower(): k for k in NODE_CREDENTIAL_MAP}
    result = []
    for name in integrations:
        key = name.lower().replace(" ", "").replace("-", "")
        if key in lookup:
            result.append(lookup[key])
    return result


def _build_context_message(
    intent_summary: str,
    required_integrations: List[str],
    required_nodes: List[str],
) -> str:
    """Build the Phase 0 context injection message for the first turn."""
    lines = ["[Phase 0 Context]"]
    if intent_summary:
        lines.append(f"Workflow intent: {intent_summary}")
    if required_integrations:
        lines.append(f"Required integrations: {', '.join(required_integrations)}")
    if required_nodes:
        lines.append(f"Required node types: {', '.join(required_nodes)}")
    lines.append("Please start by scanning credentials.")
    newline = chr(10)
    return newline.join(lines)
