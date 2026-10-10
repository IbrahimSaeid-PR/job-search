from __future__ import annotations

from pathlib import Path

import pandas as pd

from app.models.job import JobCandidate


def _safe(value):
    """Prefix cells that spreadsheets would interpret as formulas (web text is untrusted)."""
    if isinstance(value, str) and value[:1] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + value
    return value


def _frame(jobs: list[JobCandidate]) -> pd.DataFrame:
    frame = pd.DataFrame([
        {
            "Title": j.title,
            "Company": j.company,
            "Location": j.location,
            "Work Mode": j.work_mode or "",
            "Employment Type": j.employment_type or "",
            "Experience": j.experience_level or "",
            "Salary": j.salary or "",
            "Posted At": j.posted_at.isoformat() if j.posted_at else "",
            "Source": j.source,
            "Score": j.score,
            "Match Reasons": "; ".join(j.match_reasons),
            "URL": j.url,
            "Snippet": j.snippet,
        }
        for j in jobs
    ])
    return frame.apply(lambda column: column.map(_safe)) if not frame.empty else frame


def export_csv(jobs: list[JobCandidate], path: str | Path) -> Path:
    path = Path(path)
    _frame(jobs).to_csv(path, index=False, encoding="utf-8-sig")
    return path


def export_excel(jobs: list[JobCandidate], path: str | Path) -> Path:
    path = Path(path)
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        _frame(jobs).to_excel(writer, index=False, sheet_name="Jobs")
        ws = writer.book["Jobs"]
        ws.freeze_panes = "A2"
        ws.auto_filter.ref = ws.dimensions
        for column_cells in ws.columns:
            width = min(60, max(12, max(len(str(c.value or "")) for c in column_cells) + 2))
            ws.column_dimensions[column_cells[0].column_letter].width = width
    return path
