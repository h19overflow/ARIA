"""Pydantic models for execution results and error classification."""
from pydantic import BaseModel, Field



class DebuggerOutput(BaseModel):
    """Structured output from the unified Debugger agent.

    Combines classification and fix into a single LLM call, halving
    latency and token cost on the critical recovery path.
    """
    error_type: str = Field(description="One of: schema, auth, rate_limit, logic, missing_node")
    node_name: str = Field(description="Name of the failing n8n node")
    message: str = Field(description="Human-readable error summary")
    description: str | None = Field(default=None)
    # Fix fields — only populated when error_type is fixable (schema / logic)
    fixed_parameters: dict | None = Field(
        default=None,
        description="Updated parameters for the failing node. Null for auth/rate_limit.",
    )


class HITLExplanation(BaseModel):
    """LLM output for plain-English error explanation."""
    explanation: str

