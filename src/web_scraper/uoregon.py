"""Scrape the public University of Oregon Computer Science faculty directory."""

from __future__ import annotations

import argparse
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag

from web_scraper.config import ScrapeConfig
from web_scraper.exporters import export_rows
from web_scraper.http_client import Fetcher
from web_scraper.normalization import clean_email, clean_text, valid_email

DIRECTORY_URL = "https://cas.uoregon.edu/directory/computer-science-faculty"
DEPARTMENT = "Computer Science"
COLUMNS = [
    "first_name",
    "last_name",
    "title",
    "department",
    "email",
    "profile_url",
    "source_url",
]
USER_AGENT = (
    "Mihir-Trivedi-UO-Faculty-Scraper/1.0 "
    "(+https://github.com/mtrivediLU/Web-Scrapper; educational assessment)"
)


@dataclass(frozen=True, slots=True)
class FacultyRecord:
    first_name: str
    last_name: str
    title: str
    department: str
    email: str
    profile_url: str
    source_url: str

    def as_row(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class RunSummary:
    pages_processed: int
    extracted_rows: int
    exported_rows: int
    duplicates_removed: int
    missing_field_values: int
    invalid_emails: int


def split_name(name: str) -> tuple[str, str]:
    """Keep middle names with the given-name portion and preserve punctuation."""
    parts = clean_text(name).split()
    if len(parts) < 2:
        return (parts[0], "") if parts else ("", "")
    return " ".join(parts[:-1]), parts[-1]


def _field_text(row: Tag, selector: str) -> str:
    values = [clean_text(node.get_text(" ", strip=True)) for node in row.select(selector)]
    return " | ".join(value for value in values if value)


def parse_directory_page(html: str, source_url: str) -> list[FacultyRecord]:
    """Parse the listing rows rendered in the public Drupal directory HTML."""
    soup = BeautifulSoup(html, "lxml")
    records: list[FacultyRecord] = []
    for row in soup.select(".view-content > .listing__row"):
        name_link = row.select_one("h2.views-field-lname a[href]")
        profile_url = urljoin(source_url, str(name_link.get("href", ""))) if name_link else ""
        name = clean_text(name_link.get_text(" ", strip=True)) if name_link else ""
        email_link = row.select_one(".views-field-email a[href^='mailto:']")
        email = clean_email(email_link.get("href", "")) if email_link else ""
        if email and not valid_email(email):
            email = ""
        title = _field_text(
            row,
            ".views-field-job-title > .field-content, .views-field-job-title2 > .field-content",
        )
        first_name, last_name = split_name(name)
        record = FacultyRecord(
            first_name=first_name,
            last_name=last_name,
            title=title,
            department=DEPARTMENT,
            email=email,
            profile_url=profile_url,
            source_url=source_url,
        )
        if any((record.first_name, record.last_name, record.email, record.profile_url)):
            records.append(record)
    return records


def alphabetical_page_urls(html: str, source_url: str) -> list[str]:
    """Return unique alphabetical directory filters in page order."""
    soup = BeautifulSoup(html, "lxml")
    urls: list[str] = []
    for link in soup.select(".pager-alphabetical a[href]"):
        url = urljoin(source_url, str(link["href"]))
        if url not in urls:
            urls.append(url)
    return urls


def deduplicate(records: Iterable[FacultyRecord]) -> tuple[list[FacultyRecord], int]:
    unique: list[FacultyRecord] = []
    seen: set[str] = set()
    removed = 0
    for record in records:
        key = (
            f"email:{record.email.lower()}"
            if record.email
            else f"profile:{record.profile_url.lower()}"
        )
        if not key or key in seen:
            removed += 1
            continue
        seen.add(key)
        unique.append(record)
    return unique, removed


def scrape(directory_url: str = DIRECTORY_URL) -> tuple[list[FacultyRecord], RunSummary]:
    """Fetch every public alphabetical directory page at approximately one request/second."""
    config = ScrapeConfig(
        name="uoregon-computer-science-faculty",
        mode="static",
        start_urls=[directory_url],
        timeout_seconds=20,
        requests_per_second=1,
        retries=2,
        user_agent=USER_AGENT,
        respect_robots_txt=True,
    )
    with Fetcher(config) as fetcher:
        index_html = fetcher.get_text(directory_url)
        pages = alphabetical_page_urls(index_html, directory_url)
        if not pages:
            pages = [directory_url]
        extracted: list[FacultyRecord] = []
        for page_url in pages:
            extracted.extend(parse_directory_page(fetcher.get_text(page_url), page_url))
    records, duplicates = deduplicate(extracted)
    missing = sum(not value for record in records for value in record.as_row().values())
    invalid_emails = sum(not valid_email(record.email) for record in records if record.email)
    return records, RunSummary(
        pages_processed=1 + len(pages),
        extracted_rows=len(extracted),
        exported_rows=len(records),
        duplicates_removed=duplicates,
        missing_field_values=missing,
        invalid_emails=invalid_emails,
    )


def write_submission(output_dir: str | Path = "submission") -> RunSummary:
    """Run the live scrape and create the required CSV and accessible Excel files."""
    records, summary = scrape()
    destination = Path(output_dir)
    rows = [record.as_row() for record in records]
    export_rows(rows, destination / "uoregon_computer_science_faculty.csv", COLUMNS, "Faculty")
    export_rows(rows, destination / "uoregon_computer_science_faculty.xlsx", COLUMNS, "Faculty")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", default="submission")
    args = parser.parse_args()
    summary = write_submission(args.output_dir)
    for key, value in asdict(summary).items():
        print(f"{key.replace('_', ' ')}: {value}")


if __name__ == "__main__":
    main()
