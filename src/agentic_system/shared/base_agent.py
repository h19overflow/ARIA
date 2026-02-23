from __future__ import annotations

from typing import Any, AsyncIterator, Type, TypeVar

from langchain.agents import create_agent
from langchain_core.messages import AIMessageChunk, BaseMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import BaseTool
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel

from src.api.settings import settings

S = TypeVar("S", bound=BaseModel)


class BaseAgent:
    """
    Wrapper around langchain.agents.create_agent backed by ChatGoogleGenerativeAI.

    Hides model construction, tool binding, and structured-output wiring.
    Every agent in preflight/ and build_cycle/ inherits from this.

    Usage
    -----
    Streaming tokens:
        async for token in agent.stream(messages): ...

    Streaming all events (tool calls, sub-chain steps, etc.):
        async for event in agent.stream_events(messages): ...

    Structured response:
        result: MySchema = await agent.structured(messages, MySchema)

    Plain invoke:
        msg = await agent.invoke(messages)
    """

    def __init__(
        self,
        *,
        tools: list[BaseTool] | None = None,
        prompt: str | None = None,
        schema: Type[S] | None = None,
        thinking_budget: int | None = None,
        max_tokens: int | None = None,
        temperature: float = 1.0,
    ) -> None:
        self._system_prompt = prompt
        self._output_schema = schema

        model = ChatGoogleGenerativeAI(
            model=settings.gemini_model,
            api_key=settings.gemini_api_key or settings.google_api_key,
            temperature=temperature,
            max_tokens=max_tokens,
            thinking_budget=thinking_budget,
        )

        self._agent = create_agent(
            model=model,
            tools=tools or [],
            system_prompt=prompt,
            response_format=schema,
        )

    # ── Internal ──────────────────────────────────────────────────────────

    def _wrap_input(self, messages: list[BaseMessage]) -> dict[str, Any]:
        return {"messages": messages}

    # ── Public API ────────────────────────────────────────────────────────

    async def invoke(
        self,
        messages: list[BaseMessage],
        config: RunnableConfig | None = None,
    ) -> Any:
        """Single call. Returns last AIMessage or structured_response if schema set."""
        result = await self._agent.ainvoke(self._wrap_input(messages), config=config)
        if self._output_schema:
            return result.get("structured_response")
        return result["messages"][-1]

    async def stream(
        self,
        messages: list[BaseMessage],
        config: RunnableConfig | None = None,
    ) -> AsyncIterator[str]:
        """Yield raw text tokens as they arrive."""
        async for _, data in self._agent.astream(
            self._wrap_input(messages),
            config=config,
            stream_mode="messages",
        ):
            token: AIMessageChunk = data[0]
            if token.content:
                yield token.content

    async def stream_events(
        self,
        messages: list[BaseMessage],
        config: RunnableConfig | None = None,
        include_types: list[str] | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """
        Yield LangChain stream events (v2) from the agent graph.

        Key events:
          on_chat_model_stream  → data["chunk"].content  (token delta)
          on_tool_start         → data["input"]          (tool args)
          on_tool_end           → data["output"]         (tool result)
          on_chat_model_end     → data["output"]         (full message)
        """
        kwargs: dict[str, Any] = {"version": "v2"}
        if include_types:
            kwargs["include_types"] = include_types

        async for event in self._agent.astream_events(
            self._wrap_input(messages), config=config, **kwargs
        ):
            yield event

    # ── Convenience helpers ───────────────────────────────────────────────

    @staticmethod
    def token_delta(event: dict[str, Any]) -> str | None:
        """Extract text token from an on_chat_model_stream event."""
        if event.get("event") == "on_chat_model_stream":
            return event["data"]["chunk"].content or None
        return None

    @staticmethod
    def tool_start(event: dict[str, Any]) -> tuple[str, dict] | None:
        """Extract (tool_name, args) from an on_tool_start event."""
        if event.get("event") == "on_tool_start":
            return event["name"], event["data"].get("input", {})
        return None

    @staticmethod
    def tool_end(event: dict[str, Any]) -> tuple[str, Any] | None:
        """Extract (tool_name, result) from an on_tool_end event."""
        if event.get("event") == "on_tool_end":
            return event["name"], event["data"].get("output")
        return None
