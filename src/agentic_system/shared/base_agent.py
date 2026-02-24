from __future__ import annotations

import weave
from typing import Any, AsyncIterator, Generic, Type, TypeVar, Union, cast, AsyncGenerator

from langchain.agents import create_agent
from langchain_core.messages import AIMessage, AIMessageChunk, BaseMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import BaseTool
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from src.api.settings import settings
from src.agentic_system.shared.weave_logger import ensure_weave_init

S = TypeVar("S", bound=BaseModel)

# Transient errors worth retrying on Gemini
_RETRYABLE = (TimeoutError, ConnectionError, OSError)


class BaseAgent(Generic[S]):
    """
    Wrapper around langchain.agents.create_agent backed by ChatGoogleGenerativeAI.

    Hides model construction, tool binding, structured-output wiring, and retries.
    Every agent in preflight/ and build_cycle/ inherits from this.

    Usage
    -----
    Plain invoke (returns AIMessage or parsed schema instance):
        msg = await agent.invoke(messages)

    Streaming tokens:
        async for token in agent.stream(messages): ...

    Streaming all graph events (tool calls, sub-chain steps, etc.):
        async for event in agent.stream_events(messages): ...

    Passing extra state keys:
        override _build_input() in subclass to inject workflow_id etc.
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
        name: str | None = None,
        max_retries: int = 3,
    ) -> None:
        self._system_prompt = prompt
        self._output_schema = schema
        self._max_retries = max_retries
        self.name = name or self.__class__.__name__

        model = ChatGoogleGenerativeAI(
            model=settings.gemini_model,
            api_key=settings.gemini_api_key or settings.google_api_key,
            temperature=temperature,
            max_tokens=max_tokens,
            thinking_budget=thinking_budget,
        )

        self._tools_list: list[BaseTool] = tools or []
        self._agent = create_agent(
            model=model,
            tools=self._tools_list,
            system_prompt=prompt,
            response_format=schema,
            name=self.name,
        )
        ensure_weave_init()

    # ── Internal ──────────────────────────────────────────────────────────

    def _build_input(
        self, messages: list[BaseMessage], **kwargs: Any
    ) -> dict[str, Any]:
        """
        Build the graph input dict.

        Override in subclasses to inject extra state keys
        (e.g. workflow_id, run_context) alongside messages.
        """
        return {"messages": messages, **kwargs}

    def _make_retry(self) -> Any:
        return retry(
            retry=retry_if_exception_type(_RETRYABLE),
            wait=wait_exponential(multiplier=1, min=1, max=10),
            stop=stop_after_attempt(self._max_retries),
            reraise=True,
        )

    # ── Public API ────────────────────────────────────────────────────────

    @weave.op
    async def invoke(
        self,
        messages: list[BaseMessage],
        config: RunnableConfig | None = None,
        **kwargs: Any,
    ) -> Union[S, AIMessage]:
        """
        Single call.

        Returns the parsed schema instance (S) if a schema was set at
        construction, otherwise the last AIMessage.
        """

        @self._make_retry()
        async def _call() -> Union[S, AIMessage]:
            result = await self._agent.ainvoke(
                cast(Any, self._build_input(messages, **kwargs)), config=config
            )
            if self._output_schema:
                return cast(S, result.get("structured_response"))
            return cast(AIMessage, result["messages"][-1])

        return await _call()

    async def stream(
        self,
        messages: list[BaseMessage],
        config: RunnableConfig | None = None,
        include_tool_events: bool = False,
        **kwargs: Any,
    ) -> AsyncGenerator[Any, None]:
        """
        Yield content tokens as they arrive.

        By default yields only text strings (str).
        Set include_tool_events=True to also yield tool-call dicts:
            {"type": "tool_start", "name": ..., "args": ...}
            {"type": "tool_chunk", "chunks": [...]}
        """
        async for _, data in self._agent.astream(
            cast(Any, self._build_input(messages, **kwargs)),
            config=config,
            stream_mode="messages",
        ):
            token = cast(AIMessageChunk, data[0])
            if token.content:
                yield token.content
            elif include_tool_events and token.tool_call_chunks:
                yield {"type": "tool_chunk", "chunks": token.tool_call_chunks}

    async def stream_events(
        self,
        messages: list[BaseMessage],
        config: RunnableConfig | None = None,
        include_types: list[str] | None = None,
        **kwargs: Any,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """
        Yield LangChain stream events (v2) from the agent graph.

        Key events:
          on_chat_model_stream  → data["chunk"].content  (token delta)
          on_tool_start         → data["input"]          (tool args)
          on_tool_end           → data["output"]         (tool result)
          on_chat_model_end     → data["output"]         (full message)
        """
        stream_kwargs: dict[str, Any] = {"version": "v2"}
        if include_types:
            stream_kwargs["include_types"] = include_types

        async for event in self._agent.astream_events(
            cast(Any, self._build_input(messages, **kwargs)), config=config, **stream_kwargs
        ):
            yield cast(dict[str, Any], event)

    # ── Convenience helpers ───────────────────────────────────────────────

    @staticmethod
    def token_delta(event: dict[str, Any]) -> str | None:
        """Extract text token from an on_chat_model_stream event."""
        if event.get("event") != "on_chat_model_stream":
            return None
        content = event["data"]["chunk"].content
        if not content:
            return None
        # Gemini returns content as a list of blocks, not a plain string
        if isinstance(content, list):
            text = "".join(
                block.get("text", "") if isinstance(block, dict) else str(block)
                for block in content
            )
            return text or None
        return str(content)

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
