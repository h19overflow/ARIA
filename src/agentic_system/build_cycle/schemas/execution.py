"""Pydantic models for execution results and error classification."""
from pydantic import BaseModel, Field


class ClassifiedErrorOutput(BaseModel):
    """Structured output from the Error Classifier agent."""
    error_type: str = Field(description="One of: schema, auth, rate_limit, logic")
    node_name: str = Field(description="Name of the failing n8n node")
    message: str = Field(description="Human-readable error summary")
    description: str | None = Field(default=None, description="Detailed error description")
    line_number: int | None = Field(default=None, description="Line number if applicable")
    suggested_fix: str | None = Field(default=None, description="Suggested fix approach")
