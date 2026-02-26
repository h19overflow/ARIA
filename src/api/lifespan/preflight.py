from fastapi import Request

from src.agentic_system.preflight.agent import PreflightAgent

_agent: PreflightAgent | None = None


async def startup() -> None:
    global _agent
    _agent = PreflightAgent()


async def shutdown() -> None:
    global _agent
    _agent = None


def get_preflight_agent(request: Request) -> PreflightAgent:  # noqa: ARG001
    if _agent is None:
        raise RuntimeError("PreflightAgent not initialised — lifespan not running")
    return _agent
