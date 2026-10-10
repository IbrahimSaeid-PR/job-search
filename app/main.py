from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.models.job import SearchResponse
from app.models.search import SearchSpecification
from app.services.jobs import deduplicate, enrich_result, normalize_result
from app.services.search import DDGS, DemoSearchService, SearchService, build_queries

app = FastAPI(title="JobFinder Local Backend", version="1.2.0")
app.add_middleware(CORSMiddleware, allow_origin_regex=r"http://(127\.0\.0\.1|localhost)(:\d+)?")


async def _enrich(raw: list[dict], warnings: list[str], limit: int = 12) -> list[dict]:
    """Fetch page text for the first few results; failures never break the search."""
    if DDGS is None:
        warnings.append("Page details are unavailable because the ddgs package is not installed.")
        return raw
    semaphore = asyncio.Semaphore(4)

    async def enrich_one(item: dict) -> dict:
        url = str(item.get("url") or "").strip()
        if not url:
            return item
        async with semaphore:
            try:
                payload = await asyncio.wait_for(asyncio.to_thread(DDGS().extract, url), timeout=10)
                return enrich_result(item, payload or {})
            except Exception:
                return item

    head = list(await asyncio.gather(*(enrich_one(item) for item in raw[:limit])))
    return head + raw[limit:]


@app.get("/health")
async def health() -> dict:
    return {
        "ok": True,
        "service": "jobfinder-local-backend",
        "time": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/api/status")
async def status() -> dict:
    return {"ok": True, "search": "public-web", "backend": f"{settings.backend_host}:{settings.backend_port}"}


@app.post("/api/search", response_model=SearchResponse)
async def search(spec: SearchSpecification, demo_mode: bool = False) -> SearchResponse:
    started = time.perf_counter()
    queries = build_queries(spec)
    warnings: list[str] = []

    if demo_mode:
        raw = DemoSearchService.query(spec)
        warnings.append("Offline sample data is active.")
    else:
        service = SearchService()
        raw, search_warnings = await service.search_many(
            queries,
            specification=spec,
            max_results=min(settings.max_search_results_per_query, 20),
        )
        warnings.extend(search_warnings)
        if not raw:
            warnings.append("No live results were returned. Check your connection or broaden the search.")

    # Enrich only a small subset. Search itself remains useful even if page extraction fails.
    if not demo_mode and raw:
        raw = await _enrich(raw, warnings)

    jobs = []
    for item in raw[: settings.max_candidates_before_ranking]:
        try:
            normalized = normalize_result(item, spec)
            if normalized:
                jobs.append(normalized)
        except Exception as exc:
            warnings.append(f"A result could not be processed: {exc}")

    unique_jobs = deduplicate(jobs)
    ranked = sorted(unique_jobs, key=lambda job: job.score, reverse=True)[: spec.result_limit]

    return SearchResponse(
        jobs=ranked,
        total_found=len(raw),
        total_after_deduplication=len(unique_jobs),
        search_queries=queries,
        warnings=warnings,
        duration_ms=int((time.perf_counter() - started) * 1000),
    )
