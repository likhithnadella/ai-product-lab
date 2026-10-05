from typing import Literal

from pydantic import BaseModel, Field, field_validator


class IntakeRecord(BaseModel):
    """Canonical record independent of the source system."""

    source: str
    external_id: str | None = None
    email: str | None = None
    phone: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    company: str | None = None
    attributes: dict[str, str] = Field(default_factory=dict)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str | None) -> str | None:
        return value.strip().lower() if value else value

    @field_validator("phone")
    @classmethod
    def normalize_phone(cls, value: str | None) -> str | None:
        if not value:
            return value
        digits = "".join(ch for ch in value if ch.isdigit())
        return digits[-10:] if len(digits) >= 10 else digits


class MatchCandidate(BaseModel):
    record_id: str
    score: float = Field(ge=0, le=1)
    reasons: list[str]


class ResolutionResult(BaseModel):
    decision: str
    confidence: float = Field(ge=0, le=1)
    candidate: MatchCandidate | None = None
    needs_review: bool = False


class IngestionItemResult(BaseModel):
    source: str
    external_id: str | None
    status: Literal["created", "updated", "unchanged", "rejected"]
    reason: str | None = None


class BatchIngestionResult(BaseModel):
    total: int
    created: int
    updated: int
    unchanged: int
    rejected: int
    items: list[IngestionItemResult]
