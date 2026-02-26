"""Async HTTP client for the n8n REST API."""
from __future__ import annotations

import asyncio

import httpx

from src.api.settings import settings
from src.boundary.n8n._internals import parse_credential_schema, parse_credentials


class N8nClient:
    """Thin async wrapper around n8n REST endpoints used by ARIA agents."""

    def __init__(self) -> None:
        self._base = settings.n8n_base_url.rstrip("/")
        self._headers = {
            "X-N8N-API-KEY": settings.n8n_api_key,
            "Content-Type": "application/json",
        }
        self._client: httpx.AsyncClient | None = None

    async def connect(self) -> None:
        self._client = httpx.AsyncClient(
            base_url=self._base,
            headers=self._headers,
            timeout=30.0,
        )

    async def disconnect(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    # -- Workflows --

    async def deploy_workflow(self, workflow_json: dict) -> dict:
        """POST /api/v1/workflows -- create a new workflow."""
        resp = await self._client.post("/api/v1/workflows", json=workflow_json)
        resp.raise_for_status()
        return resp.json()

    async def activate_workflow(self, workflow_id: str) -> dict:
        """POST /api/v1/workflows/{id}/activate."""
        resp = await self._client.post(
            f"/api/v1/workflows/{workflow_id}/activate",
        )
        resp.raise_for_status()
        return resp.json()

    async def deactivate_workflow(self, workflow_id: str) -> dict:
        """POST /api/v1/workflows/{id}/deactivate."""
        resp = await self._client.post(
            f"/api/v1/workflows/{workflow_id}/deactivate",
        )
        resp.raise_for_status()
        return resp.json()

    async def update_workflow(self, workflow_id: str, workflow_json: dict) -> dict:
        """PUT /api/v1/workflows/{id} -- update existing workflow."""
        resp = await self._client.put(f"/api/v1/workflows/{workflow_id}", json=workflow_json)
        resp.raise_for_status()
        return resp.json()

    async def delete_workflow(self, workflow_id: str) -> None:
        """DELETE /api/v1/workflows/{id}."""
        resp = await self._client.delete(
            f"/api/v1/workflows/{workflow_id}",
        )
        resp.raise_for_status()

    # -- Executions --

    async def trigger_webhook(
        self, webhook_path: str, payload: dict | None = None, *, test_mode: bool = False,
    ) -> dict:
        """POST /webhook[‑test]/{path} — use test_mode=True for n8n UI test runs."""
        prefix = "webhook-test" if test_mode else "webhook"
        resp = await self._client.post(
            f"/{prefix}/{webhook_path}", json=payload or {}
        )
        resp.raise_for_status()
        return resp.json()

    async def poll_execution(
        self,
        workflow_id: str,
        *,
        timeout: float = 30.0,
        interval: float = 1.0,
    ) -> dict:
        """Poll GET /api/v1/executions until stoppedAt is set."""
        elapsed = 0.0
        while elapsed < timeout:
            resp = await self._client.get(
                "/api/v1/executions",
                params={"workflowId": workflow_id, "limit": "1"},
            )
            resp.raise_for_status()
            data = resp.json()
            executions = data.get("data", [])
            if executions and executions[0].get("stoppedAt"):
                return executions[0]
            await asyncio.sleep(interval)
            elapsed += interval
        raise TimeoutError(
            f"Execution for workflow {workflow_id} "
            f"did not complete in {timeout}s",
        )

    async def run_workflow(self, workflow_id: str) -> dict:
        """POST /api/v1/workflows/{id}/run — trigger a manual execution."""
        resp = await self._client.post(f"/api/v1/workflows/{workflow_id}/run")
        resp.raise_for_status()
        return resp.json()

    # -- Credentials --

    async def list_credentials(self) -> list[dict]:
        """GET /api/v1/credentials -- list all saved credentials."""
        resp = await self._client.get("/api/v1/credentials")
        resp.raise_for_status()
        return parse_credentials(resp.json().get("data", []))

    async def get_credential_schema(self, credential_type: str) -> dict:
        """GET /api/v1/credentials/schema/{credentialType}."""
        resp = await self._client.get(f"/api/v1/credentials/schema/{credential_type}")
        resp.raise_for_status()
        return parse_credential_schema(resp.json())

    async def list_credential_types(self) -> list[dict]:
        """GET /api/v1/credentials/schema -- all available credential types."""
        resp = await self._client.get("/api/v1/credentials/schema")
        resp.raise_for_status()
        return resp.json().get("data", [])

    async def save_credential(self, credential_type: str, name: str, data: dict) -> dict:
        """POST /api/v1/credentials -- save a new credential.

        Fetches the credential schema first and backfills missing fields
        with type-appropriate defaults so n8n's strict validation passes.
        """
        schema = await self.get_credential_schema(credential_type)
        full_data = _backfill_credential_data(data, schema)
        payload = {"type": credential_type, "name": name, "data": full_data}
        resp = await self._client.post("/api/v1/credentials", json=payload)
        resp.raise_for_status()
        return resp.json()

    # -- Workflows (read) --

    async def get_workflow(self, workflow_id: str) -> dict:
        """GET /api/v1/workflows/{id}."""
        resp = await self._client.get(f"/api/v1/workflows/{workflow_id}")
        resp.raise_for_status()
        return resp.json()

    async def list_workflows(self, limit: int = 50) -> list[dict]:
        """GET /api/v1/workflows?limit=N."""
        resp = await self._client.get("/api/v1/workflows", params={"limit": limit})
        resp.raise_for_status()
        return resp.json().get("data", [])


# Type → safe default value for missing credential fields.
# Booleans default to False (won't activate allOf if/then branches).
# Strings/notices default to "".  Enums are skipped (no safe default).
_BACKFILL_DEFAULTS: dict[str, object] = {
    "string": "",
    "notice": "",
    "boolean": False,
}


def _backfill_credential_data(user_data: dict, schema: dict) -> dict:
    """Merge user-supplied data with schema defaults for missing fields.

    n8n requires certain fields to be present even when optional —
    especially booleans that gate allOf/if-then conditional branches.
    Strips unknown keys since n8n uses additionalProperties: false.
    """
    known_fields = {prop["name"] for prop in schema.get("properties", [])}
    result = {k: v for k, v in user_data.items() if k in known_fields}
    for prop in schema.get("properties", []):
        field_name = prop["name"]
        if field_name in result:
            continue
        if prop.get("conditional"):
            continue  # skip fields gated by a boolean — adding them violates allOf else branch
        field_type = prop.get("type", "string")
        if field_type in _BACKFILL_DEFAULTS and not prop.get("enum"):
            result[field_name] = _BACKFILL_DEFAULTS[field_type]
    return result
