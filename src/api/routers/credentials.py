"""Direct credential saving endpoint (bypasses LangGraph interrupt)."""
from __future__ import annotations

import logging

import httpx
from fastapi import APIRouter, Depends, HTTPException

from src.api.lifespan.n8n import get_n8n
from src.api.schemas import SaveCredentialRequest, SaveCredentialResponse
from src.boundary.n8n.client import N8nClient

log = logging.getLogger("aria.api.credentials")
router = APIRouter(prefix="/credentials", tags=["credentials"])


@router.post("", response_model=SaveCredentialResponse)
async def save_credential(
    body: SaveCredentialRequest,
    client: N8nClient = Depends(get_n8n),
) -> SaveCredentialResponse:
    """Save credential directly to n8n."""
    log.info("POST /credentials | type=%s name=%s", body.credential_type, body.name)
    try:
        result = await client.save_credential(body.credential_type, body.name, body.data)
    except httpx.HTTPStatusError as exc:
        n8n_body = exc.response.text
        log.error(
            "n8n rejected credential save | type=%s status=%s body=%s",
            body.credential_type, exc.response.status_code, n8n_body,
        )
        raise HTTPException(
            status_code=502,
            detail=f"n8n rejected the credential save: {n8n_body}",
        ) from exc
    except httpx.HTTPError as exc:
        log.error("n8n unreachable during credential save | type=%s error=%s", body.credential_type, exc)
        raise HTTPException(status_code=502, detail="Could not reach n8n") from exc

    cred_id = result.get("id", "")
    log.info("Credential saved | id=%s type=%s", cred_id, body.credential_type)
    return SaveCredentialResponse(
        credential_id=cred_id,
        credential_type=body.credential_type,
        name=body.name,
    )
