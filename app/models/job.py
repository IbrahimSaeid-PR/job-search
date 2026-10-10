from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class JobCandidate(BaseModel):
    title: str
    company: str = "Unknown company"
    location: str = "Not specified"
    work_mode: str | None = None
    employment_type: str | None = None
    experience_level: str | None = None
    salary: str | None = None
    posted_at: datetime | None = None
    source: str = "Web"
    url: str
    snippet: str = ""
    score: float = 0.0
    match_reasons: list[str] = Field(default_factory=list)
    validated: bool = False


class SearchResponse(BaseModel):
    jobs: list[JobCandidate]
    total_found: int
    total_after_deduplication: int
    search_queries: list[str]
    warnings: list[str] = Field(default_factory=list)
    duration_ms: int
