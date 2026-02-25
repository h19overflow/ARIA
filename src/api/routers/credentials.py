"""Direct credential saving endpoint (bypasses LangGraph interrupt)."""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.boundary.n8n.client import N8nClient

log = logging.getLogger("aria.api.credentials")
router = APIRouter(prefix="/credentials", tags=["credentials"])


class SaveCredentialRequest(BaseModel):
    credential_type: str
    name: str
    data: dict[str, str]


class SaveCredentialResponse(BaseModel):
    credential_id: str
    credential_type: str
    name: str


@router.post("", response_model=SaveCredentialResponse)
async def save_credential(body: SaveCredentialRequest) -> SaveCredentialResponse:
    """Save credential directly to n8n."""
    log.info("POST /credentials | type=%s name=%s", body.credential_type, body.name)
    client = N8nClient()
    await client.connect()
    try:
        result = await client.save_credential(body.credential_type, body.name, body.data)
        cred_id = result.get("id", "")
        log.info("Credential saved | id=%s type=%s", cred_id, body.credential_type)
        return SaveCredentialResponse(
            credential_id=cred_id,
            credential_type=body.credential_type,
            name=body.name,
        )
    except Exception as exc:
        log.error("Failed to save credential | type=%s error=%s", body.credential_type, exc)
        raise HTTPException(status_code=500, detail=f"Failed to save credential: {exc}") from exc
    finally:
        await client.disconnect()
