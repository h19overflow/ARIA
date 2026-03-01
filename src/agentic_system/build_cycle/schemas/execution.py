"""Pydantic models for execution results and error classification."""
from pydantic import BaseModel, Field


class FixedNode(BaseModel):
    """A patch for an existing node in the workflow."""
    node_name: str = Field(description="Exact name of the existing node to patch")
    parameters: dict = Field(description="Complete replacement parameters for this node")
    new_type: str | None = Field(
        default=None,
        description="New n8n node type if the node type needs changing (e.g. substitution)",
    )
    credentials: dict | None = Field(
        default=None,
        description="Credentials to attach, e.g. {'gmailOAuth2Api': {'id': 'cred-123', 'name': 'gmailOAuth2Api'}}",
    )


class NewNode(BaseModel):
    """A new node to add to the workflow."""
    name: str = Field(description="Display name for the new node")
    type: str = Field(description="n8n node type (e.g. 'n8n-nodes-base.code')")
    parameters: dict = Field(description="Complete n8n node parameters")
    position: list[int] = Field(description="Canvas position [x, y]")
    credentials: dict | None = Field(
        default=None,
        description="Credentials to attach if the node requires auth",
    )


class DebuggerOutput(BaseModel):
    """Structured output from the unified Debugger agent.

    Supports full-spectrum fixes: parameter patches, node type changes,
    node additions/removals, and connection rewiring.
    """
    error_type: str = Field(description="One of: schema, auth, rate_limit, logic, missing_node")
    node_name: str = Field(description="Name of the primary failing n8n node")
    message: str = Field(description="Human-readable error summary")
    description: str | None = Field(default=None)

    # Fix fields — None means "no fix attempted" (unfixable error types)
    fixed_nodes: list[FixedNode] | None = Field(
        default=None,
        description="Patches for existing nodes. Each entry replaces that node's parameters (and optionally type/credentials).",
    )
    fixed_connections: dict | None = Field(
        default=None,
        description="Complete replacement connections dict for the workflow. Only set if rewiring is needed.",
    )
    added_nodes: list[NewNode] | None = Field(
        default=None,
        description="New nodes to insert into the workflow.",
    )
    removed_node_names: list[str] | None = Field(
        default=None,
        description="Names of nodes to remove from the workflow.",
    )


class HITLExplanation(BaseModel):
    """LLM output for plain-English error explanation."""
    explanation: str
