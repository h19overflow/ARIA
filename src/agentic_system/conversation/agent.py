import asyncio
import logging
from typing import Any, AsyncGenerator, Dict, List

from langchain.agents import create_agent

from src.agentic_system.shared.base_agent import BaseAgent
from src.agentic_system.shared.node_credential_map import NODE_CREDENTIAL_MAP
from .state import get_state, save_state, ConversationState
from .schemas import ConversationNotes
from .prompts import CONVERSATION_SYSTEM_PROMPT
from .tools import (
    batch_notes, take_note, commit_notes,
    make_scan_credentials, get_credential_schema, save_credential, commit_preflight,
)
from .message_builders import build_lc_messages
from .event_handlers import (
    handle_tool_end_state,
    capture_ai_message,
    capture_tool_message,
    extract_result_string,
)

logger = logging.getLogger(__name__)


def _integrations_to_node_keys(integrations: list[str]) -> list[str]:
    """Map service names (e.g. 'Telegram') to n8n node keys."""
    lookup = {k.lower(): k for k in NODE_CREDENTIAL_MAP}
    result = []
    for name in integrations:
        key = name.lower().replace(" ", "").replace("-", "")
        if key in lookup:
            result.append(lookup[key])
        else:
            logger.warning(
                "No node mapping for integration %r — skipping credential scan for it",
                name,
            )
    return result


class ConversationAgent(BaseAgent):
    """
    Phase 0 Conversation Agent.
    Handles multi-turn requirements gathering and state persistence.
    """

    def __init__(self, name: str = "ConversationAgent"):
        super().__init__(
            tools=[batch_notes, take_note, commit_notes],
            prompt=CONVERSATION_SYSTEM_PROMPT,
            name=name,
            model_name="gemini-3-flash-preview",
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

        agent_graph = self._build_agent_graph_for_state(state)
        lc_messages = build_lc_messages(state.messages)

        try:
            current_tool_calls: List[Dict[str, Any]] = []
            async for event in agent_graph.astream_events(
                {"messages": lc_messages}, version="v2"
            ):
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

    def _build_agent_graph_for_state(self, state: ConversationState) -> Any:
        """Build an agent graph appropriate for the current conversation phase.

        In credential mode (after commit_notes, before commit_preflight),
        creates a per-request graph with credential tools bound to the
        required nodes. Otherwise returns the default agent graph.
        """
        if not state.committed or state.notes.credentials_committed:
            return self._agent

        required_nodes = _integrations_to_node_keys(
            state.notes.required_integrations,
        )
        state.notes.required_nodes = required_nodes

        credential_tools = [
            batch_notes, take_note, commit_notes,
            make_scan_credentials(required_nodes),
            get_credential_schema, save_credential, commit_preflight,
        ]
        return create_agent(
            model=self._model,
            tools=credential_tools,
            system_prompt=self._system_prompt,
            name=self.name,
        )

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
                state, tool_name, tool_result, current_tool_calls
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
