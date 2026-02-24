"""Pydantic models for workflow generation."""
from pydantic import BaseModel, Field


class WorkflowNode(BaseModel):
    """A single n8n workflow node."""
    name: str = Field(description="Display name of the node")
    type: str = Field(description="n8n node type (e.g. n8n-nodes-base.slack)")
    parameters: dict = Field(default_factory=dict, description="Node parameters")
    position: list[int] = Field(default_factory=lambda: [0, 0])
    credentials: dict = Field(default_factory=dict, description="Credential references")


class WorkflowConnection(BaseModel):
    """Connection between two nodes."""
    source: str = Field(description="Source node name")
    target: str = Field(description="Target node name")
    source_output: int = Field(default=0)
    target_input: int = Field(default=0)


class EngineerOutput(BaseModel):
    """Structured output from the Engineer agent."""
    workflow_name: str = Field(description="Name for the workflow")
    nodes: list[WorkflowNode] = Field(description="All nodes in the workflow")
    connections: list[WorkflowConnection] = Field(description="Node connections")


class FixOutput(BaseModel):
    """Structured output from the Fix agent."""
    node_name: str = Field(description="Name of the node being fixed")
    fixed_parameters: dict = Field(description="Updated parameters for the node")
    explanation: str = Field(description="What was fixed and why")
