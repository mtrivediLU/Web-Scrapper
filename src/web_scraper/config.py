"""YAML configuration loading and validation."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

import yaml

Mode = Literal["static", "javascript", "api"]
DEFAULT_USER_AGENT = "web-scraper-interview-demo/0.1 (+https://github.com/mtrivediLU/Web-Scrapper)"


@dataclass(slots=True)
class FieldSpec:
    selector: str
    attribute: str | None = None
    strip_prefix: str | None = None


@dataclass(slots=True)
class PaginationSpec:
    selector: str | None = None
    attribute: str = "href"
    next_path: str | None = None
    max_pages: int = 20


@dataclass(slots=True)
class ScrapeConfig:
    name: str
    mode: Mode
    start_urls: list[str]
    record_selector: str | None = None
    records_path: str | None = None
    fields: dict[str, FieldSpec | str] = field(default_factory=dict)
    pagination: PaginationSpec = field(default_factory=PaginationSpec)
    required_fields: list[str] = field(default_factory=lambda: ["name", "email"])
    fixture_dir: Path | None = None
    timeout_seconds: float = 15.0
    requests_per_second: float = 1.0
    retries: int = 3
    user_agent: str = DEFAULT_USER_AGENT
    respect_robots_txt: bool = True


def _field_spec(value: Any) -> FieldSpec | str:
    if isinstance(value, str):
        return value
    if not isinstance(value, dict) or "selector" not in value:
        raise ValueError("HTML field definitions must have a selector")
    return FieldSpec(
        selector=str(value["selector"]),
        attribute=value.get("attribute"),
        strip_prefix=value.get("strip_prefix"),
    )


def load_config(path: str | Path) -> ScrapeConfig:
    """Load a scrape configuration relative to its YAML file."""
    config_path = Path(path).resolve()
    with config_path.open(encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}
    if not isinstance(raw, dict):
        raise ValueError("Configuration root must be a mapping")

    mode = raw.get("mode", "static")
    if mode not in {"static", "javascript", "api"}:
        raise ValueError("mode must be static, javascript, or api")
    start_urls = raw.get("start_urls", [])
    if not isinstance(start_urls, list) or not start_urls:
        raise ValueError("start_urls must be a non-empty list")
    fields = raw.get("fields", {})
    if not isinstance(fields, dict):
        raise ValueError("fields must be a mapping")
    fixture_dir = raw.get("fixture_dir")
    pagination_raw = raw.get("pagination", {}) or {}
    if not isinstance(pagination_raw, dict):
        raise ValueError("pagination must be a mapping")

    return ScrapeConfig(
        name=str(raw.get("name", config_path.stem)),
        mode=mode,
        start_urls=[str(url) for url in start_urls],
        record_selector=raw.get("record_selector"),
        records_path=raw.get("records_path"),
        fields={key: _field_spec(value) for key, value in fields.items()},
        pagination=PaginationSpec(
            selector=pagination_raw.get("selector"),
            attribute=str(pagination_raw.get("attribute", "href")),
            next_path=pagination_raw.get("next_path"),
            max_pages=int(pagination_raw.get("max_pages", 20)),
        ),
        required_fields=[str(field) for field in raw.get("required_fields", ["name", "email"])],
        fixture_dir=(config_path.parent / str(fixture_dir)).resolve() if fixture_dir else None,
        timeout_seconds=float(raw.get("timeout_seconds", 15)),
        requests_per_second=float(raw.get("requests_per_second", 1)),
        retries=int(raw.get("retries", 3)),
        user_agent=str(raw.get("user_agent", DEFAULT_USER_AGENT)),
        respect_robots_txt=bool(raw.get("respect_robots_txt", True)),
    )
