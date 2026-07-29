"""Small, explicit data-cleaning helpers."""

from __future__ import annotations

import re
from collections.abc import Iterable

from web_scraper.models import PersonRecord

EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def clean_text(value: object) -> str:
    """Collapse non-breaking spaces and repeated whitespace into one space."""
    return " ".join(str(value or "").replace("\xa0", " ").split())


def clean_email(value: object) -> str:
    return clean_text(value).removeprefix("mailto:").strip().lower()


def valid_email(email: str) -> bool:
    return not email or bool(EMAIL_RE.fullmatch(email))


def normalize(record: PersonRecord) -> PersonRecord:
    values = {key: clean_text(value) for key, value in record.as_dict().items()}
    values["email"] = clean_email(record.email)
    return PersonRecord(**values)


def deduplicate(records: Iterable[PersonRecord]) -> tuple[list[PersonRecord], int]:
    """Prefer email, then profile URL, then a stable name/institution fallback."""
    unique: list[PersonRecord] = []
    seen: set[str] = set()
    duplicates = 0
    for record in records:
        key = (
            f"email:{record.email.lower()}"
            if record.email
            else f"profile:{record.profile_url.lower()}"
            if record.profile_url
            else f"person:{record.name.lower()}|{record.institution.lower()}"
        )
        if key in seen:
            duplicates += 1
            continue
        seen.add(key)
        unique.append(record)
    return unique, duplicates
