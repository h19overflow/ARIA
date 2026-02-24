import asyncio
import logging
from typing import AsyncGenerator, Any, Dict, List

from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, ToolMessage, BaseMessage

from src.agentic_system.shared.base_agent import BaseAgent
from .state import get_state, save_state, ConversationState
from .schemas import ConversationNotes
from .prompts import PHASE_0_SYSTEM_PROMPT
from .tools import take_note, commit_notes

logger = logging.getLogger(__name__)

class ConversationAgent(BaseAgent):
    """
    Phase 0 Conversation Agent.
    Handles multi-turn requirements gathering and state persistence.
    Inherits from BaseAgent to leverage shared model construction, 
    retries, and event streaming.
    """
    def __init__(self, name: str = "ConversationAgent"):
        super().__init__(
            tools=[take_note, commit_notes],
            prompt=PHASE_0_SYSTEM_PROMPT,
            name=name
        )

    async def initialize_conversation(self, conversation_id: str) -> None:
        """Initialize the Redis state for a new conversation."""
        state = ConversationState(
            conversation_id=conversation_id,
            messages=[],
            notes=ConversationNotes(),
            committed=False
        )
        await save_state(state)

    async def process_message(self, conversation_id: str, user_message: str) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Process a user message, stream tokens, execute tools concurrently,
        and save state. Yields SSE events.
        """
        # 1. Retrieve state
        state = await get_state(conversation_id)
        if not state:
            state = ConversationState(
                conversation_id=conversation_id,
                messages=[],
                notes=ConversationNotes(),
                committed=False
            )

        # 2. Append user message
        state.messages.append({"role": "user", "content": user_message})

        # 3. Prepare LangChain messages from state
        lc_messages: List[BaseMessage] = []
        for msg in state.messages:
            if msg["role"] == "user":
                lc_messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                kwargs = {"content": msg.get("content", "")}
                if "tool_calls" in msg and msg["tool_calls"]:
                    kwargs["tool_calls"] = msg["tool_calls"]
                if "invalid_tool_calls" in msg and msg["invalid_tool_calls"]:
                    kwargs["invalid_tool_calls"] = msg["invalid_tool_calls"]
                lc_messages.append(AIMessage(**kwargs))
            elif msg["role"] == "tool":
                lc_messages.append(ToolMessage(content=msg.get("content", ""), tool_call_id=msg.get("tool_call_id", "")))

        # 4. Run LLM loop using BaseAgent's stream_events
        try:
            current_tool_calls = []
            
            async for event in self.stream_events(lc_messages):
                # Token streaming
                token = self.token_delta(event)
                if token:
                    # Normalize: Gemini sometimes returns a list of content blocks
                    if isinstance(token, list):
                        text = "".join(
                            block.get("text", "") if isinstance(block, dict) else str(block)
                            for block in token
                        )
                    else:
                        text = str(token)
                    if text:
                        yield {"type": "token", "content": text}
                
                # Tool start (capture tool call args)
                tool_start_info = self.tool_start(event)
                if tool_start_info:
                    tool_name, tool_args = tool_start_info
                    current_tool_calls.append({"name": tool_name, "args": tool_args})
                    
                # Tool end (capture tool result and update state)
                tool_end_info = self.tool_end(event)
                if tool_end_info:
                    tool_name, tool_result = tool_end_info
                    
                    # Update ConversationNotes based on the tool that was executed
                    tool_args = next((tc["args"] for tc in reversed(current_tool_calls) if tc["name"] == tool_name), {})
                    
                    if tool_name == "take_note":
                        self._update_notes_state(state, tool_args)
                        yield {"type": "tool_event", "tool": "take_note", "data": tool_args}
                    elif tool_name == "commit_notes":
                        state.notes.summary = tool_args.get("summary", "")
                        state.committed = True
                        yield {"type": "tool_event", "tool": "commit_notes", "data": tool_args}
                        
                # Capture AIMessages to save to state
                if event.get("event") == "on_chat_model_end":
                    ai_msg = event["data"].get("output")
                    if isinstance(ai_msg, AIMessage):
                        state_msg = {"role": "assistant", "content": ai_msg.content or ""}
                        if hasattr(ai_msg, "tool_calls") and ai_msg.tool_calls:
                            state_msg["tool_calls"] = ai_msg.tool_calls
                        if hasattr(ai_msg, "invalid_tool_calls") and ai_msg.invalid_tool_calls:
                            state_msg["invalid_tool_calls"] = ai_msg.invalid_tool_calls
                        state.messages.append(state_msg)
                        
                # Capture ToolMessages to save to state
                if event.get("event") == "on_tool_end":
                    # Tool output could be a string or a ToolMessage depending on the underlying agent executor
                    # If it's just the output, we might need to construct the ToolMessage
                    tool_output = event["data"].get("output")
                    tool_name = event.get("name")
                    
                    # Find the corresponding tool_call_id from the AIMessage's tool_calls
                    tool_call_id = ""
                    if state.messages and state.messages[-1]["role"] == "assistant":
                        tcs = state.messages[-1].get("tool_calls", [])
                        for tc in tcs:
                            if tc["name"] == tool_name:
                                tool_call_id = tc["id"]
                                break
                    
                    if isinstance(tool_output, ToolMessage):
                        state.messages.append({
                            "role": "tool",
                            "content": tool_output.content,
                            "tool_call_id": tool_output.tool_call_id
                        })
                    else:
                        state.messages.append({
                            "role": "tool",
                            "content": str(tool_output),
                            "tool_call_id": tool_call_id
                        })
            
        except asyncio.CancelledError:
            logger.info(f"Stream cancelled for conversation {conversation_id}")
            raise
        except Exception as e:
            logger.error(f"Error in conversation agent: {e}", exc_info=True)
            yield {"type": "error", "content": str(e)}
        finally:
            # 5. Save state after the turn
            await save_state(state)

    def _update_notes_state(self, state: ConversationState, args: Dict[str, Any]):
        """Update the notes in the state based on take_note arguments."""
        key = args.get("key")
        value = args.get("value")
        
        if key:
            if value is None:
                # Delete note
                if key in state.notes.raw_notes:
                    del state.notes.raw_notes[key]
                if hasattr(state.notes, key):
                    if key in ["constraints", "required_integrations"]:
                        setattr(state.notes, key, [])
                    elif key == "data_transform":
                        setattr(state.notes, key, None)
                    else:
                        setattr(state.notes, key, "")
            else:
                # Set note
                state.notes.raw_notes[key] = value
                if hasattr(state.notes, key):
                    if key in ["constraints", "required_integrations"]:
                        current = getattr(state.notes, key)
                        if value not in current:
                            current.append(value)
                    else:
                        setattr(state.notes, key, value)
