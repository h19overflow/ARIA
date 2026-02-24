"""Structured output schema for the CredentialScanner agent."""
from __future__ import annotations

from pydantic import BaseModel, Field


class ScannerOutput(BaseModel):
    """Result of scanning required node types against saved n8n credentials."""

    resolved: dict[str, str] = Field(
        default_factory=dict,
        description="Mapping of credential_type -> credential_id for types with exactly one saved match.",
    )
    pending: list[str] = Field(
        default_factory=list,
        description="Credential types that have no saved credential in n8n.",
    )
    ambiguous: dict[str, list[dict]] = Field(
        default_factory=dict,
        description="Credential types with multiple saved matches: {cred_type: [{id, name}, ...]}.",
    )
    summary: str = Field(
        description="One-line human summary, e.g. '2 resolved, 1 pending, 0 ambiguous'.",
    )
