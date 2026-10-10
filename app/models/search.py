from __future__ import annotations

from enum import Enum
from typing import Annotated

from pydantic import BaseModel, Field, field_validator


class JobPostingAge(str, Enum):
    LAST_24_HOURS = "Last 24 Hours"
    LAST_2_DAYS = "Last 2 Days"
    LAST_3_DAYS = "Last 3 Days"
    LAST_4_DAYS = "Last 4 Days"
    LAST_5_DAYS = "Last 5 Days"
    LAST_6_DAYS = "Last 6 Days"
    LAST_7_DAYS = "Last 7 Days"

    @property
    def days(self) -> int:
        return 1 if self is JobPostingAge.LAST_24_HOURS else int(self.value.split()[1])


class ExperienceLevel(str, Enum):
    INTERNSHIP = "Internship"
    ENTRY_LEVEL = "Entry Level"
    JUNIOR = "Junior"
    MID_LEVEL = "Mid Level"
    SENIOR = "Senior"
    LEAD = "Lead"
    ANY = "Any"


class WorkMode(str, Enum):
    REMOTE = "Remote"
    HYBRID = "Hybrid"
    ON_SITE = "On-site"


class EmploymentType(str, Enum):
    FULL_TIME = "Full-time"
    PART_TIME = "Part-time"
    INTERNSHIP = "Internship"
    CONTRACT = "Contract"
    TEMPORARY = "Temporary"
    ANY = "Any"


class SalaryRange(BaseModel):
    minimum: float | None = Field(default=None, ge=0)
    maximum: float | None = Field(default=None, ge=0)
    currency: str = Field(default="USD", min_length=3, max_length=3)

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        return value.upper().strip()

    @field_validator("maximum")
    @classmethod
    def validate_maximum(cls, value: float | None, info):
        minimum = info.data.get("minimum")
        if value is not None and minimum is not None and value < minimum:
            raise ValueError("Maximum salary must be greater than or equal to minimum salary")
        return value


class SearchSpecification(BaseModel):
    job_titles: Annotated[list[str], Field(min_length=1, max_length=5)]
    additional_roles: list[str] = Field(default_factory=list, max_length=8)
    location: str | None = Field(default=None, max_length=120)
    posting_age: JobPostingAge = JobPostingAge.LAST_7_DAYS
    salary: SalaryRange | None = None
    experience_level: ExperienceLevel | None = ExperienceLevel.ANY
    work_modes: list[WorkMode] = Field(default_factory=list, max_length=3)
    employment_types: list[EmploymentType] = Field(default_factory=list, max_length=6)
    keywords: list[str] = Field(default_factory=list, max_length=20)
    excluded_keywords: list[str] = Field(default_factory=list, max_length=20)
    result_limit: int = Field(default=50, ge=1, le=50)

    @field_validator("job_titles", "additional_roles", "keywords", "excluded_keywords")
    @classmethod
    def clean_terms(cls, values: list[str]) -> list[str]:
        seen: set[str] = set()
        cleaned: list[str] = []
        for item in values:
            value = " ".join(item.strip().split())
            if value and value.casefold() not in seen:
                seen.add(value.casefold())
                cleaned.append(value)
        return cleaned

    @field_validator("job_titles")
    @classmethod
    def require_title(cls, values: list[str]) -> list[str]:
        if not values:
            raise ValueError("At least one non-empty job title is required")
        return values

    @field_validator("location")
    @classmethod
    def clean_location(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = " ".join(value.strip().split())
        return value or None
