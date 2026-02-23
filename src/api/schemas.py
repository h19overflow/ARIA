from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Ingestion
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Workflows (job submission)
# ---------------------------------------------------------------------------

class WorkflowRequest(BaseModel):
    description: str


class WorkflowResponse(BaseModel):
    job_id: str
    status: str


# ---------------------------------------------------------------------------
# Jobs
# ---------------------------------------------------------------------------

class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    result: dict | None = None
    error: str | None = None
