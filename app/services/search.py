from __future__ import annotations

import asyncio
import re
from typing import Any

try:
    from ddgs import DDGS
except ImportError:  # Keeps the local backend importable with a clear runtime warning.
    DDGS = None  # type: ignore[assignment]

from app.config import settings
from app.models.search import SearchSpecification


def build_queries(specification: SearchSpecification) -> list[str]:
    """Create a small deterministic set of web searches from the form values."""
    roles = specification.job_titles + specification.additional_roles
    role_text = " OR ".join(f'"{role}"' for role in roles)
    if len(roles) > 1:
        role_text = f"({role_text})"
    location = specification.location or ""
    mode = " ".join(mode.value for mode in specification.work_modes)
    experience = (
        specification.experience_level.value
        if specification.experience_level and specification.experience_level.value != "Any"
        else ""
    )
    keywords = " ".join(specification.keywords[:6])

    queries = [
        f"{role_text} {location} jobs",
        f"{role_text} {location} {mode} {experience} jobs",
        f"{role_text} {location} {keywords} jobs",
        f"site:linkedin.com/jobs {role_text} {location}",
        f"site:indeed.com {role_text} {location}",
        f"site:greenhouse.io {role_text} {location}",
        f"site:lever.co {role_text} {location}",
    ]
    return list(dict.fromkeys(" ".join(q.split()) for q in queries if q.strip()))


class SearchService:
    """Public-web job discovery. No LLM or AI service is required."""

    def __init__(self, region: str | None = None, backend: str | None = None):
        self.region = region or settings.search_region
        self.backend = backend or settings.search_backend

    @staticmethod
    def _time_limit(spec: SearchSpecification) -> str | None:
        days = spec.posting_age.days
        return "d" if days == 1 else "w"

    def _search_sync(self, query: str, max_results: int, timelimit: str | None) -> list[dict[str, Any]]:
        if DDGS is None:
            raise RuntimeError("The ddgs package is not installed. Run: pip install ddgs")
        results = DDGS().text(
            query,
            region=self.region,
            safesearch="moderate",
            timelimit=timelimit,
            max_results=max_results,
            backend=self.backend,
        )
        return list(results or [])

    async def search_many(
        self,
        queries: list[str],
        *,
        specification: SearchSpecification,
        max_results: int,
    ) -> tuple[list[dict[str, Any]], list[str]]:
        warnings: list[str] = []
        semaphore = asyncio.Semaphore(3)
        if DDGS is None:
            return [], ["The ddgs package is not installed. Run: pip install ddgs"]
        timelimit = self._time_limit(specification)

        async def run_one(query: str) -> list[dict[str, Any]]:
            async with semaphore:
                try:
                    rows = await asyncio.to_thread(self._search_sync, query, max_results, timelimit)
                    return [
                        {
                            "title": row.get("title", ""),
                            "url": row.get("href", ""),
                            "snippet": row.get("body", ""),
                            "source": row.get("source") or "",
                        }
                        for row in rows
                    ]
                except Exception as exc:
                    warnings.append(f"Search failed for '{query}': {exc}")
                    return []

        batches = await asyncio.gather(*(run_one(query) for query in queries))
        return [item for batch in batches for item in batch], warnings


class DemoSearchService:
    """Small offline dataset retained for local testing and installer verification."""

    DATA = [
        {"title": "Junior Python Backend Engineer", "company": "Northstar Labs", "location": "Remote", "url": "https://example.com/jobs/python-backend", "snippet": "Python, FastAPI, PostgreSQL, REST APIs. Remote. Posted today."},
        {"title": "AI Engineer", "company": "Orbit Analytics", "location": "Cairo, Egypt · Hybrid", "url": "https://example.com/jobs/ai-engineer", "snippet": "LLM applications, Python, RAG and evaluation. Hybrid role."},
        {"title": "Machine Learning Engineer", "company": "Vertex Mobility", "location": "Giza, Egypt", "url": "https://example.com/jobs/ml-engineer", "snippet": "scikit-learn, feature engineering, model evaluation and data pipelines."},
        {"title": "Software Engineer - Python", "company": "BrightStack", "location": "Remote", "url": "https://example.com/jobs/python-software", "snippet": "Backend services in Python. Full-time. Remote within selected regions."},
        {"title": "Data Engineer", "company": "BlueRiver", "location": "Cairo, Egypt · On-site", "url": "https://example.com/jobs/data-engineer", "snippet": "SQL, Python, ETL, analytics engineering and cloud data platforms."},
        {"title": "GenAI Intern", "company": "Mosaic AI", "location": "Cairo, Egypt · Hybrid", "url": "https://example.com/jobs/genai-intern", "snippet": "Prompt engineering, Python and RAG projects for production prototypes."},
    ]

    @classmethod
    def query(cls, specification: SearchSpecification) -> list[dict[str, Any]]:
        wanted = " ".join(specification.job_titles + specification.additional_roles + specification.keywords).lower()
        tokens = [token for token in re.findall(r"\w+", wanted) if len(token) >= 3]
        blocked = [x.lower() for x in specification.excluded_keywords]
        results = []
        for item in cls.DATA:
            haystack = f"{item['title']} {item['company']} {item['location']} {item['snippet']}".lower()
            if blocked and any(term in haystack for term in blocked):
                continue
            if tokens and not any(token in haystack for token in tokens):
                continue
            results.append(item)
        return results or cls.DATA[:3]
