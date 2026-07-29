from pathlib import Path

from web_scraper.config import load_config
from web_scraper.extractors import api_pages, parse_api, parse_html, static_pages
from web_scraper.http_client import Fetcher

ROOT = Path(__file__).parents[1]


def test_html_parsing_extracts_configured_fields_and_relative_profile_url() -> None:
    config = load_config(ROOT / "configs/faculty.yaml")
    with Fetcher(config) as fetcher:
        source, html = next(static_pages(config, fetcher))
        records = parse_html(html, source, config, fetcher)
    assert len(records) == 2
    assert records[0].name == "Dr. Alice   Nguyen"
    assert records[0].email == "Alice.Nguyen@Example.edu"
    assert records[0].profile_url == "fixture://faculty/people/alice-nguyen"
    assert records[0].source_url == "fixture://faculty/page1.html"
    assert records[0].scraped_at


def test_static_pagination_follows_two_fixture_pages() -> None:
    config = load_config(ROOT / "configs/faculty.yaml")
    with Fetcher(config) as fetcher:
        pages = list(static_pages(config, fetcher))
    assert [url for url, _ in pages] == [
        "fixture://faculty/page1.html",
        "fixture://faculty/page2.html",
    ]


def test_api_parsing_and_pagination() -> None:
    config = load_config(ROOT / "configs/api.yaml")
    with Fetcher(config) as fetcher:
        pages = list(api_pages(config, fetcher))
    assert len(pages) == 2
    records = parse_api(pages[0][1], pages[0][0], config)
    assert records[0].name == "Dr. Alice Nguyen"
    assert records[0].profile_url == "fixture://faculty/people/alice-nguyen"
