"""Orchestration of extraction, data quality checks, deduplication, and export."""

from __future__ import annotations

from web_scraper.config import ScrapeConfig
from web_scraper.exporters import export_records
from web_scraper.extractors import api_pages, javascript_pages, parse_api, parse_html, static_pages
from web_scraper.http_client import Fetcher
from web_scraper.models import PersonRecord, QualitySummary
from web_scraper.normalization import deduplicate, normalize, valid_email


def quality_summary(
    records: list[PersonRecord], duplicates_removed: int, required: list[str]
) -> QualitySummary:
    return QualitySummary(
        extracted_rows=len(records),
        duplicates_removed=duplicates_removed,
        invalid_emails=sum(not valid_email(record.email) for record in records),
        rows_with_missing_required_fields=sum(
            any(not getattr(record, field, "") for field in required) for record in records
        ),
    )


def run(config: ScrapeConfig, output: str) -> tuple[list[PersonRecord], QualitySummary]:
    """Run one configured scrape and write the cleaned, deduplicated records."""
    extracted: list[PersonRecord] = []
    if config.mode == "javascript":
        with Fetcher(config) as fetcher:
            for source_url, html in javascript_pages(config, fetcher):
                extracted.extend(parse_html(html, source_url, config, fetcher))
    else:
        with Fetcher(config) as fetcher:
            if config.mode == "static":
                for source_url, html in static_pages(config, fetcher):
                    extracted.extend(parse_html(html, source_url, config, fetcher))
            elif config.mode == "api":
                for source_url, payload in api_pages(config, fetcher):
                    extracted.extend(parse_api(payload, source_url, config))
            else:
                raise ValueError(f"Unsupported mode: {config.mode}")
    cleaned = [normalize(record) for record in extracted]
    unique, duplicates = deduplicate(cleaned)
    summary = quality_summary(unique, duplicates, config.required_fields)
    summary.extracted_rows = len(extracted)
    export_records(unique, output)
    return unique, summary
