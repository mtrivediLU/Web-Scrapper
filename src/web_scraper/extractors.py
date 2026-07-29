"""Static HTML, Playwright, and JSON extraction implementations."""

from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag

from web_scraper.config import FieldSpec, ScrapeConfig
from web_scraper.http_client import Fetcher
from web_scraper.models import PersonRecord


def get_path(value: Any, path: str | None) -> Any:
    """Read a dotted mapping path; list items are addressed by numeric components."""
    if not path:
        return value
    current = value
    for part in path.split("."):
        if isinstance(current, dict):
            current = current.get(part)
        elif isinstance(current, list) and part.isdigit():
            current = current[int(part)] if int(part) < len(current) else None
        else:
            return None
    return current


def _html_value(node: Tag, spec: FieldSpec) -> str:
    match = node.select_one(spec.selector)
    if match is None:
        return ""
    value = match.get(spec.attribute, "") if spec.attribute else match.get_text(" ", strip=True)
    if isinstance(value, list):
        value = " ".join(value)
    result = str(value)
    return result.removeprefix(spec.strip_prefix) if spec.strip_prefix else result


def parse_html(
    html: str, source_url: str, config: ScrapeConfig, fetcher: Fetcher
) -> list[PersonRecord]:
    if not config.record_selector:
        raise ValueError("Static and JavaScript configurations require record_selector")
    soup = BeautifulSoup(html, "lxml")
    records: list[PersonRecord] = []
    for node in soup.select(config.record_selector):
        values: dict[str, str] = {}
        for field, spec in config.fields.items():
            if not isinstance(spec, FieldSpec):
                raise ValueError("HTML fields must use selector mappings")
            value = _html_value(node, spec)
            if field in {"profile_url"} and value:
                value = fetcher.resolve_url(source_url, value)
            values[field] = value
        values["source_url"] = source_url
        records.append(PersonRecord.with_timestamp(**values))
    return records


def parse_api(payload: Any, source_url: str, config: ScrapeConfig) -> list[PersonRecord]:
    rows = get_path(payload, config.records_path)
    if not isinstance(rows, list):
        raise ValueError("records_path must point to a JSON list")
    records: list[PersonRecord] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        values = {
            field: str(get_path(row, spec) or "")
            for field, spec in config.fields.items()
            if isinstance(spec, str)
        }
        profile_url = values.get("profile_url")
        if profile_url:
            if source_url.startswith("fixture://") and not profile_url.startswith("fixture://"):
                values["profile_url"] = f"{source_url.rsplit('/', 1)[0]}/{profile_url.lstrip('/')}"
            else:
                values["profile_url"] = urljoin(source_url, profile_url)
        values["source_url"] = source_url
        records.append(PersonRecord.with_timestamp(**values))
    return records


def static_pages(config: ScrapeConfig, fetcher: Fetcher) -> Iterator[tuple[str, str]]:
    """Yield configured HTML pages and selector-based next pages, once each."""
    queue = list(config.start_urls)
    visited: set[str] = set()
    while queue and len(visited) < config.pagination.max_pages:
        url = queue.pop(0)
        if url in visited:
            continue
        visited.add(url)
        html = fetcher.get_text(url)
        yield url, html
        if config.pagination.selector:
            soup = BeautifulSoup(html, "lxml")
            next_link = soup.select_one(config.pagination.selector)
            if next_link:
                target = next_link.get(config.pagination.attribute)
                if target:
                    queue.append(fetcher.resolve_url(url, str(target)))


def api_pages(config: ScrapeConfig, fetcher: Fetcher) -> Iterator[tuple[str, Any]]:
    queue = list(config.start_urls)
    visited: set[str] = set()
    while queue and len(visited) < config.pagination.max_pages:
        url = queue.pop(0)
        if url in visited:
            continue
        visited.add(url)
        payload = json.loads(fetcher.get_text(url))
        yield url, payload
        next_url = get_path(payload, config.pagination.next_path)
        if isinstance(next_url, str) and next_url:
            queue.append(fetcher.resolve_url(url, next_url))


def javascript_pages(config: ScrapeConfig, fetcher: Fetcher) -> Iterator[tuple[str, str]]:
    """Render pages using Playwright when the optional dependency is installed."""
    try:
        from playwright.sync_api import sync_playwright  # type: ignore[import-not-found]
    except ImportError as error:
        raise RuntimeError("Install Playwright support: pip install -e '.[playwright]'") from error
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(user_agent=config.user_agent)
        try:
            queue = list(config.start_urls)
            visited: set[str] = set()
            while queue and len(visited) < config.pagination.max_pages:
                url = queue.pop(0)
                if url in visited:
                    continue
                visited.add(url)
                fetcher.prepare_request(url)
                page.goto(url, wait_until="networkidle", timeout=int(config.timeout_seconds * 1000))
                html = page.content()
                yield page.url, html
                if config.pagination.selector:
                    soup = BeautifulSoup(html, "lxml")
                    next_link = soup.select_one(config.pagination.selector)
                    if next_link and (target := next_link.get(config.pagination.attribute)):
                        queue.append(fetcher.resolve_url(page.url, str(target)))
        finally:
            browser.close()
