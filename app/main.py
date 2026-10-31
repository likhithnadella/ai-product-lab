import os

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field

from app.body_limit import DemoBodyLimitMiddleware
from app.ingestion import InMemoryRecordStore, ingest_batch
from app.models import BatchIngestionResult, IntakeRecord, ResolutionResult
from app.resolution import resolve

app = FastAPI(
    title="AI Product Lab — Data Operations API",
    version="0.2.0",
    description="A production-minded foundation for cleansing, resolution, search, and AI-assisted workflows.",
)

app.add_middleware(DemoBodyLimitMiddleware)

record_store = InMemoryRecordStore()


def require_unsafe_demo_opt_in() -> None:
    """Fail closed unless a developer explicitly opts into unauthenticated local demos.

    This is an operational guard, NOT authentication or network isolation.
    Never set the flag for an internet-facing deployment.
    """
    if os.environ.get("AI_PRODUCT_LAB_ENABLE_UNAUTHENTICATED_DEMO") != "1":
        raise HTTPException(status_code=503, detail="Unauthenticated demo API is disabled")


class ResolveRequest(BaseModel):
    incoming: IntakeRecord
    candidates: list[IntakeRecord] = Field(max_length=1000)


class IngestRequest(BaseModel):
    records: list[IntakeRecord] = Field(max_length=1000)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post(
    "/v1/resolve",
    response_model=ResolutionResult,
    dependencies=[Depends(require_unsafe_demo_opt_in)],
)
def resolve_record(request: ResolveRequest) -> ResolutionResult:
    return resolve(request.incoming, request.candidates)


@app.post(
    "/v1/ingest",
    response_model=BatchIngestionResult,
    dependencies=[Depends(require_unsafe_demo_opt_in)],
)
def ingest_records(request: IngestRequest) -> BatchIngestionResult:
    return ingest_batch(request.records, record_store)
