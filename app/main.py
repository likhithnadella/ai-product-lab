from fastapi import FastAPI
from pydantic import BaseModel

from app.ingestion import InMemoryRecordStore, ingest_batch
from app.models import BatchIngestionResult, IntakeRecord, ResolutionResult
from app.resolution import resolve

app = FastAPI(
    title="AI Product Lab — Data Operations API",
    version="0.2.0",
    description="A production-minded foundation for cleansing, resolution, search, and AI-assisted workflows.",
)

record_store = InMemoryRecordStore()


class ResolveRequest(BaseModel):
    incoming: IntakeRecord
    candidates: list[IntakeRecord]


class IngestRequest(BaseModel):
    records: list[IntakeRecord]


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/v1/resolve", response_model=ResolutionResult)
def resolve_record(request: ResolveRequest) -> ResolutionResult:
    return resolve(request.incoming, request.candidates)


@app.post("/v1/ingest", response_model=BatchIngestionResult)
def ingest_records(request: IngestRequest) -> BatchIngestionResult:
    return ingest_batch(request.records, record_store)
