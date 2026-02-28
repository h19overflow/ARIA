"""LLM fallback for credential type resolution.

Used as step 4 in the credential resolution chain when
convention guessing fails to match an integration name.
"""
import logging

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class CredentialMatch(BaseModel):
    """Structured output schema for LLM credential matching."""

    credential_types: list[str] = Field(
        description=(
            "Matching n8n credential type identifiers, "
            "or empty if none match"
        )
    )


async def llm_resolve(name: str) -> list[str] | None:
    """Ask the LLM to match an integration name to n8n credential types.

    Uses a lightweight BaseAgent call with structured output.
    Only called when convention guessing fails entirely.
    """
    from src.boundary.n8n.client import N8nClient
    from src.agentic_system.shared.base_agent import BaseAgent
    from langchain_core.messages import HumanMessage

    saved_types = await _fetch_saved_credential_types()
    if not saved_types:
        return None

    agent = BaseAgent(
        schema=CredentialMatch,
        prompt=(
            "You are a credential type matcher for n8n workflow automation. "
            "Given an integration name and a list of available credential "
            "types, return which credential type(s) match the integration. "
            "Return an empty list if none match."
        ),
        name="CredentialMatcher",
    )

    try:
        result = await agent.invoke([
            HumanMessage(content=(
                f"Integration: '{name}'\n"
                f"Available credential types: {saved_types}\n"
                f"Which credential type(s) match this integration?"
            ))
        ])
        if hasattr(result, "credential_types") and result.credential_types:
            logger.info("LLM resolved %r -> %s", name, result.credential_types)
            return result.credential_types
    except Exception as exc:
        logger.warning(
            "LLM credential resolution failed for %r: %s", name, exc,
        )

    return None


async def _fetch_saved_credential_types() -> list[str]:
    """Fetch distinct credential types currently saved in n8n."""
    from src.boundary.n8n.client import N8nClient

    client = N8nClient()
    await client.connect()
    try:
        saved = await client.list_credentials()
        return sorted(
            {c.get("type", "") for c in saved if c.get("type")}
        )
    except Exception as exc:
        logger.error("LLM resolve: failed to list credentials: %s", exc)
        return []
    finally:
        await client.disconnect()
