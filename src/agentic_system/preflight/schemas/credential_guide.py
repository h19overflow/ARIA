"""Schemas for the CredentialGuide agent output."""
from __future__ import annotations

from pydantic import BaseModel


class CredentialFieldInfo(BaseModel):
    name: str
    label: str
    description: str
    required: bool
    options: list[str] | None = None


class CredentialGuideEntry(BaseModel):
    credential_type: str
    display_name: str
    service_description: str
    how_to_obtain: str
    help_url: str
    fields: list[CredentialFieldInfo]


class CredentialGuideOutput(BaseModel):
    entries: list[CredentialGuideEntry]
    summary: str
