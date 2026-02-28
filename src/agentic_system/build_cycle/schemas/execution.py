"""Pydantic models for execution results and error classification."""
from pydantic import BaseModel, Field


class ClassifiedErrorOutput(BaseModel):
    """Structured output from the Error Classifier agent."""
    error_type: str = Field(description="One of: schema, auth, rate_limit, logic, missing_node")
    node_name: str = Field(description="Name of the failing n8n node")
    message: str = Field(description="Human-readable error summary")
    description: str | None = Field(default=None, description="Detailed error description")
    line_number: int | None = Field(default=None, description="Line number if applicable")
    suggested_fix: str | None = Field(default=None, description="Suggested fix approach")


class DebuggerOutput(BaseModel):
    """Structured output from the unified Debugger agent.

    Combines classification and fix into a single LLM call, halving
    latency and token cost on the critical recovery path.
    """
    error_type: str = Field(description="One of: schema, auth, rate_limit, logic, missing_node")
    node_name: str = Field(description="Name of the failing n8n node")
    message: str = Field(description="Human-readable error summary")
    description: str | None = Field(default=None)
    line_number: int | None = Field(default=None)
    # Fix fields — only populated when error_type is fixable (schema / logic)
    fixed_parameters: dict | None = Field(
        default=None,
        description="Updated parameters for the failing node. Null for auth/rate_limit.",
    )
    explanation: str | None = Field(
        default=None,
        description="What was changed and why. Null when no fix is attempted.",
    )
