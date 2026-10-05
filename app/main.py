from fastapi import FastAPI
from pydantic import BaseModel

from app.models import IntakeRecord, ResolutionResult
from app.resolution import resolve

app = FastAPI(
    title="AI Product Lab — Data Operations API",
    version="0.1.0",
    description="A production-minded foundation for cleansing, resolution, search, and AI-assisted workflows.",
)


class ResolveRequest(BaseModel):
    incoming: IntakeRecord
    candidates: list[IntakeRecord]


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/v1/resolve", response_model=ResolutionResult)
def resolve_record(request: ResolveRequest) -> ResolutionResult:
    return resolve(request.incoming, request.candidates)
