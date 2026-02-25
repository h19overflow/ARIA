import asyncio
import logging
from typing import AsyncGenerator, Any, Dict, List

from src.agentic_system.shared.base_agent import BaseAgent
from .state import get_state, save_state, ConversationState
from .schemas import ConversationNotes
from .prompts import PHASE_0_SYSTEM_PROMPT
from .tools import take_note, commit_notes
from .event_handlers import (
    build_lc_messages,
    handle_tool_end_state,
    capture_ai_message,
    capture_tool_message,
    extract_result_string,
)

logger = logging.getLogger(__name__)


class ConversationAgent(BaseAgent):
    """
    Phase 0 Conversation Agent.
    Handles multi-turn requirements gathering and state persistence.
    """

    def __init__(self, name: str = "ConversationAgent"):
        super().__init__(
            tools=[take_note, commit_notes],
            prompt=PHASE_0_SYSTEM_PROMPT,
            name=name,
        )

    async def initialize_conversation(self, conversation_id: str) -> None:
        """Initialize the Redis state for a new conversation."""
        state = ConversationState(
            conversation_id=conversation_id,
            messages=[],
            notes=ConversationNotes(),
            committed=False,
        )
        await save_state(state)

    async def process_message(
        self, conversation_id: str, user_message: str
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Process a user message, stream tokens, execute tools,
        and save state. Yields SSE events.
        """
        state = await self._load_or_create_state(conversation_id)
        state.messages.append({"role": "user", "content": user_message})
        lc_messages = build_lc_messages(state.messages)

        try:
            current_tool_calls: List[Dict[str, Any]] = []
            async for event in self.stream_events(lc_messages):
                async for sse in self._dispatch_event(
                    event, state, current_tool_calls
                ):
                    yield sse
        except asyncio.CancelledError:
            logger.info("Stream cancelled for conversation %s", conversation_id)
            raise
        except Exception as e:
            logger.error("Error in conversation agent: %s", e, exc_info=True)
            yield {"type": "error", "content": str(e)}
        finally:
            await save_state(state)

    # ── Private helpers ──────────────────────────────────────────────────

    async def _load_or_create_state(
        self, conversation_id: str
    ) -> ConversationState:
        """Load existing state or create a fresh one."""
        state = await get_state(conversation_id)
        if not state:
            state = ConversationState(
                conversation_id=conversation_id,
                messages=[],
                notes=ConversationNotes(),
                committed=False,
            )
        return state

    async def _dispatch_event(
        self,
        event: Dict[str, Any],
        state: ConversationState,
        current_tool_calls: List[Dict[str, Any]],
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Route a single stream event to the appropriate handler."""
        # Token streaming
        token = self._extract_token_text(event)
        if token:
            yield {"type": "token", "content": token}

        # Tool start — capture and notify frontend
        tool_start_info = self.tool_start(event)
        if tool_start_info:
            tool_name, tool_args = tool_start_info
            current_tool_calls.append({"name": tool_name, "args": tool_args})
            yield {"type": "tool_start", "tool": tool_name, "args": tool_args}

        # Tool end — notify frontend, then update state
        tool_end_info = self.tool_end(event)
        if tool_end_info:
            tool_name, tool_result = tool_end_info
            result_str = extract_result_string(tool_result)
            yield {"type": "tool_end", "tool": tool_name, "result": result_str}
            async for sse in handle_tool_end_state(
                state, tool_name, current_tool_calls
            ):
                yield sse

        # Capture messages for state persistence
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
