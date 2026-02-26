"""Service layer for the Conversation Agent."""
import uuid
from typing import AsyncGenerator, Any

from src.agentic_system.conversation.core.agent import ConversationAgent


class ConversationService:
    """Service layer abstracting the underlying Conversation Agent."""

    def __init__(self) -> None:
        self._agent = ConversationAgent()

    async def start_conversation(self) -> str:
        """Start a new conversation and return a unique ID.
        
        Returns:
            A unique conversation ID string.
        """
        conversation_id = str(uuid.uuid4())
        await self._agent.initialize_conversation(conversation_id)
        return conversation_id

    async def process_message(self, conversation_id: str, message: str) -> AsyncGenerator[Any, None]:
        """Process a message and yield events from the agent.
        
        Args:
            conversation_id: The ID of the conversation.
            message: The user's message.
            
        Yields:
            Events from the agent as dictionaries or other objects.
        """
        async for event in self._agent.process_message(conversation_id, message):
            yield event
