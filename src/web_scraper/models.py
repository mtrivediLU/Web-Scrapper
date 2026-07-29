"""Data models shared by extraction, cleaning, and export stages."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime

COLUMNS = [
    "name",
    "email",
    "job_title",
    "institution",
    "profile_url",
    "source_url",
    "scraped_at",
]


@dataclass(slots=True)
class PersonRecord:
    name: str = ""
    email: str = ""
    job_title: str = ""
    institution: str = ""
    profile_url: str = ""
    source_url: str = ""
    scraped_at: str = ""

    @classmethod
    def with_timestamp(cls, **values: str) -> PersonRecord:
        values.setdefault("scraped_at", datetime.now(UTC).isoformat())
        return cls(**values)

    def as_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(slots=True)
class QualitySummary:
    extracted_rows: int = 0
    duplicates_removed: int = 0
    invalid_emails: int = 0
    rows_with_missing_required_fields: int = 0

    def as_dict(self) -> dict[str, int]:
        return asdict(self)
