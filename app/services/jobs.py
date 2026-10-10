from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

from app.models.job import JobCandidate
from app.models.search import SearchSpecification


def _has(text: str, *words: str) -> bool:
    """Whole-word match so that 'lead' does not match 'leading' and 'intern' not 'internal'."""
    return any(re.search(rf"(?<![a-z0-9]){re.escape(w)}(?![a-z0-9])", text) for w in words)


def guess_source(url: str) -> str:
    host = urlparse(url).netloc.lower()
    mapping = {
        "linkedin.com": "LinkedIn",
        "indeed.com": "Indeed",
        "glassdoor.com": "Glassdoor",
        "wellfound.com": "Wellfound",
        "greenhouse.io": "Greenhouse",
        "lever.co": "Lever",
    }
    for domain, label in mapping.items():
        if domain in host:
            return label
    return host.replace("www.", "") or "Web"


def enrich_result(raw: dict, fetch_payload: dict) -> dict:
    """Merge fetched public-page text into a search result without assuming a site-specific schema."""
    content = fetch_payload.get("content") or fetch_payload.get("markdown") or fetch_payload.get("text") or ""
    if isinstance(content, dict):
        content = content.get("content") or ""
    content = " ".join(str(content).split())
    if content:
        raw = dict(raw)
        raw["content"] = content[:8000]
        if not raw.get("snippet"):
            raw["snippet"] = content[:1200]
        # Many job pages expose posting date in prose; capture common phrases conservatively.
        date_match = re.search(r"(?i)(?:posted|published)\s*(?:on)?\s*([A-Z][a-z]+\s+\d{1,2},\s+\d{4}|\d{4}-\d{2}-\d{2})", content)
        if date_match and not raw.get("date"):
            raw["date"] = date_match.group(1)
    if fetch_payload.get("title") and not raw.get("title"):
        raw["title"] = fetch_payload.get("title")
    return raw


def normalize_result(raw: dict, specification: SearchSpecification) -> JobCandidate | None:
    url = str(raw.get("url") or raw.get("link") or "").strip()
    title = " ".join(str(raw.get("title") or raw.get("name") or "").split())
    snippet = " ".join(str(raw.get("snippet") or raw.get("description") or raw.get("content") or "").split())
    if not url or not title:
        return None
    company = " ".join(str(raw.get("company") or "").split())
    location = str(raw.get("location") or "").strip() or "Not specified"
    text = f"{title} {snippet}"
    if not company:
        # Search-engine titles usually look like "Role - Company" or "Role | Company | Site".
        parts = [p.strip() for p in re.split(r"\s+[|–—-]\s+", title) if p.strip()]
        if len(parts) >= 2 and len(parts[1]) < 80:
            company = parts[1]
    company = company or "Unknown company"
    posted_at = raw.get("date") or raw.get("published_at") or raw.get("published")
    parsed_date = None
    if isinstance(posted_at, str):
        parsed_date = parse_posted_date(posted_at)

    haystack = f"{title} {snippet}".lower()
    if any(term.lower() in haystack for term in specification.excluded_keywords):
        return None

    source = str(raw.get("source") or guess_source(url))
    work_mode = detect_work_mode(text)
    employment_type = detect_employment(text)
    experience = detect_experience(text)
    if parsed_date is not None:
        age_days = (datetime.now(timezone.utc) - parsed_date).total_seconds() / 86400
        if age_days > specification.posting_age.days + 0.01:
            return None

    candidate = JobCandidate(
        title=title,
        company=company,
        location=location,
        work_mode=work_mode,
        employment_type=employment_type,
        experience_level=experience,
        salary=extract_salary(text),
        posted_at=parsed_date,
        source=source,
        url=url,
        snippet=snippet[:1200],
        validated=True,
    )
    candidate.score, candidate.match_reasons = score_candidate(candidate, specification)
    return candidate


def parse_posted_date(value: str) -> datetime | None:
    text = value.strip().lower()
    if not text:
        return None
    now = datetime.now(timezone.utc)
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        pass
    if text in {"today", "just posted"} or re.search(r"\b(second|minute|hour)s?\s+ago", text):
        return now
    if text == "yesterday":
        return now - timedelta(days=1)
    m = re.search(r"(\d+)\s+days?\s+ago", text)
    if m:
        return now - timedelta(days=int(m.group(1)))
    m = re.search(r"(\d+)\s+weeks?\s+ago", text)
    if m:
        return now - timedelta(days=7 * int(m.group(1)))
    m = re.search(r"(\d+)\s+months?\s+ago", text)
    if m:
        return now - timedelta(days=30 * int(m.group(1)))
    for fmt in ("%B %d, %Y", "%b %d, %Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value.strip(), fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def detect_work_mode(text: str) -> str | None:
    lower = text.lower()
    if _has(lower, "remote", "work from home", "wfh"):
        return "Remote"
    if _has(lower, "hybrid"):
        return "Hybrid"
    if _has(lower, "on-site", "onsite", "on site"):
        return "On-site"
    return None


def detect_employment(text: str) -> str | None:
    lower = text.lower()
    for terms, label in [
        (("full-time", "full time"), "Full-time"),
        (("part-time", "part time"), "Part-time"),
        (("contract", "contractor"), "Contract"),
        (("temporary",), "Temporary"),
        (("internship", "intern"), "Internship"),
    ]:
        if _has(lower, *terms):
            return label
    return None


def detect_experience(text: str) -> str | None:
    lower = text.lower()
    checks = [
        (("senior", "sr"), "Senior"),
        (("lead", "principal", "staff"), "Lead"),
        (("mid-level", "mid level", "intermediate"), "Mid Level"),
        (("junior", "jr"), "Junior"),
        (("entry level", "entry-level", "graduate", "fresh graduate"), "Entry Level"),
        (("internship", "intern"), "Internship"),
    ]
    for needles, label in checks:
        if _has(lower, *needles):
            return label
    return None


def extract_salary(text: str) -> str | None:
    amount = r"[$€£]\s?\d[\d,]*(?:\.\d+)?(?:\s?[kK])?"
    match = re.search(rf"{amount}(?:\s?(?:-|–|to)\s?(?:{amount}|\d[\d,]*(?:\.\d+)?\s?[kK]?))?", text)
    return match.group(0).strip() if match else None


def score_candidate(job: JobCandidate, specification: SearchSpecification) -> tuple[float, list[str]]:
    haystack = f"{job.title} {job.company} {job.location} {job.snippet}".lower()
    score = 0.0
    reasons: list[str] = []
    titles = specification.job_titles + specification.additional_roles
    for term in titles:
        if term.lower() in haystack:
            score += 24
            reasons.append(f"Matches role: {term}")
    for term in specification.keywords:
        if term.lower() in haystack:
            score += 8
    for term in specification.excluded_keywords:
        if term.lower() in haystack:
            score -= 40
    if specification.location and specification.location.lower() in haystack:
        score += 12
        reasons.append("Location match")
    if specification.work_modes:
        if job.work_mode in {m.value for m in specification.work_modes}:
            score += 12
            reasons.append("Work mode match")
    if specification.experience_level and specification.experience_level.value != "Any" and job.experience_level == specification.experience_level.value:
        score += 10
        reasons.append("Experience match")
    if specification.employment_types and "Any" not in {t.value for t in specification.employment_types}:
        if job.employment_type in {t.value for t in specification.employment_types}:
            score += 8
            reasons.append("Employment type match")
    if job.posted_at:
        age_days = max(0, (datetime.now(timezone.utc) - job.posted_at).total_seconds() / 86400)
        if age_days <= specification.posting_age.days:
            score += 8
            reasons.append("Posting age verified")
    if job.source in {"LinkedIn", "Indeed", "Greenhouse", "Lever"}:
        score += 3
    score += min(8, len(job.snippet) / 150)
    return round(score, 2), reasons


_TRACKING_PARAMS = {"utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content", "fbclid", "gclid", "ref", "trk", "trackingid"}


def normalize_url(url: str) -> str:
    """Canonical form used for duplicate detection (no fragment, tracking params, www or trailing slash)."""
    parsed = urlparse(url.strip())
    query = "&".join(
        sorted(
            part for part in parsed.query.split("&")
            if part and part.split("=", 1)[0].lower() not in _TRACKING_PARAMS
        )
    )
    host = parsed.netloc.lower().removeprefix("www.")
    path = parsed.path.rstrip("/")
    return f"{host}{path}" + (f"?{query}" if query else "")


def deduplicate(jobs: list[JobCandidate]) -> list[JobCandidate]:
    seen: set[str] = set()
    result: list[JobCandidate] = []
    for job in sorted(jobs, key=lambda x: x.score, reverse=True):
        keys = {normalize_url(job.url)}
        if job.company != "Unknown company":
            keys.add(f"{job.title.lower()}|{job.company.lower()}|{job.location.lower()}")
        if keys & seen:
            continue
        seen.update(keys)
        result.append(job)
    return result
