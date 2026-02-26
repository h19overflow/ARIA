from __future__ import annotations

from typing import Any, Dict

from pydantic import BaseModel, Field

from src.api.schemas_sse import SSEEvent  # noqa: F401 — re-export for existing imports


# Ingestion

class IngestN8nResponse(BaseModel):
    type: str
    ingested: int


class IngestApiSpecRequest(BaseModel):
    source_name: str
    spec: dict


class IngestApiSpecResponse(BaseModel):
    type: str
    source: str
    ingested: int


# Workflows / Jobs

class WorkflowRequest(BaseModel):
    description: str | None = None
    conversation_id: str | None = None


class WorkflowResponse(BaseModel):
    job_id: str
    status: str


class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    result: dict | None = None
    error: str | None = None


class JobState(BaseModel):
    job_id: str
    status: str                  # "planning"|"interrupted"|"done"|"failed"
    aria_state: dict | None = None
    error: str | None = None


class ResumeRequest(BaseModel):
    """Unified HITL resume payload.

    Clarify:              {"action": "clarify", "value": "<user answer>"}
    Credential (paste):   {"action": "provide", "credentials": {"Gmail OAuth2": {...}}}
    Credential (n8n UI):  {"action": "resume"}
    Ambiguity select:     {"action": "select", "selections": {"Gmail OAuth2": "<id>"}}
    Fix retry:            {"action": "retry"}
    Fix replan:           {"action": "replan"}
    Fix abort:            {"action": "abort"}
    """
    action: str
    value: str | None = None
    credentials: dict | None = None
    selections: dict[str, str] | None = None


# Phase 0 — Conversation

class StartConversationResponse(BaseModel):
    conversation_id: str = Field(..., description="Unique identifier for the new conversation")


class MessageRequest(BaseModel):
    message: str = Field(..., description="User input message")


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Dict[str, Any]


class ErrorResponse(BaseModel):
    error: ErrorDetail


# Phase 1 — Preflight (legacy job-based)

class PreflightRequest(BaseModel):
    description: str | None = None
    conversation_id: str | None = None


class PreflightResponse(BaseModel):
    preflight_job_id: str
    status: str  # "planning"


# Phase 1 — Preflight (conversational)

class StartPreflightRequest(BaseModel):
    conversation_id: str


class StartPreflightResponse(BaseModel):
    preflight_id: str


class PreflightMessageRequest(BaseModel):
    message: str


class PreflightStatusResponse(BaseModel):
    committed: bool
    notes: dict


# Phase 2 — Build

class BuildRequest(BaseModel):
    preflight_job_id: str


class BuildResponse(BaseModel):
    build_job_id: str
    status: str  # "building"


# Credentials

class SaveCredentialRequest(BaseModel):
    credential_type: str
    name: str
    data: dict[str, object]


class SaveCredentialResponse(BaseModel):
    credential_id: str
    credential_type: str
    name: str
