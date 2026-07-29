# Web-Scrapper

A small, reusable Python 3.12 web-scraping project designed to be easy to explain and adapt during a technical interview. The distribution name stays **Web-Scrapper**; the importable package is `web_scraper`.

It demonstrates three supported approaches:

- Static HTML: HTTPX + Beautiful Soup + lxml.
- JavaScript-rendered pages: Playwright (optional extra).
- JSON/REST APIs: HTTPX + dotted JSON paths.

The included two-page university-directory HTML and JSON fixtures make the demo and test suite fully offline and repeatable.

## Setup

Use Python 3.12, ideally in a virtual environment.

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
# For JavaScript sites:
python -m pip install -e ".[playwright]"
playwright install chromium
```

Optional extras are also available for projects that need them: `.[scrapy]` and `.[selenium]`. They are deliberately not used by the core framework.

## Verified commands

The fixture configurations below require no network access:

```bash
web-scraper scrape --config configs/faculty.yaml --output outputs/faculty.xlsx
web-scraper api --config configs/api.yaml --output outputs/faculty.csv
pytest
ruff check .
mypy src
# Or: make demo api check
```

Each command prints a data-quality summary. The supplied data has four extracted rows, one duplicate removed, one malformed email, and one row missing a required `job_title`; it exports three clean records.

## Configuration

`configs/faculty.yaml` is the HTML example. The important site-specific parts are `record_selector`, field selectors, and the pagination link selector:

```yaml
mode: static
start_urls: [https://directory.example.edu/faculty]
record_selector: article.faculty-card
fields:
  name: {selector: h2.name}
  email: {selector: a.email, attribute: href, strip_prefix: "mailto:"}
  profile_url: {selector: a.profile, attribute: href}
pagination: {selector: a.next, attribute: href, max_pages: 20}
```

`configs/api.yaml` maps fields from a JSON record with dotted paths such as `contact.email`, uses `records_path` to locate the list, and `pagination.next_path` to locate the next-page URL. URLs in selectors and API values are resolved relative to the page/API endpoint.

Fixture URLs (`fixture://...`) exist only for the included offline demonstration. Replace them with a permitted `https://` URL when adapting a real target. For a real API, put secrets in `.env` (copied from `.env.example`) and add only documented, authorized headers as appropriate.

## Architecture

```text
YAML config -> Fetcher -> HTML / Playwright / API extractor
                         -> normalize -> validate + deduplicate -> CSV / Excel
```

`Fetcher` uses a descriptive user agent, timeouts, retry-with-exponential-backoff, a configurable request rate, redirects, and `robots.txt` checks before HTTP requests. It will not bypass authentication, CAPTCHA challenges, paywalls, robots rules, or other access controls. Always review a site's terms and obtain permission before scraping it.

`pipeline.py` reports extracted rows, duplicates removed, invalid emails, and rows with missing required fields. It keeps malformed-email rows visible for review rather than silently deleting evidence. Exports are UTF-8 CSV or accessible Excel: a clear header row, autofilter, frozen header row, sensible column widths, and no merged cells.

## How to adapt during an interview

1. Inspect one representative page/API response and copy `configs/faculty.yaml` or `configs/api.yaml`.
2. Change selectors or dotted paths, the record container, and pagination settings; keep the framework untouched.
3. Set the real URL, confirm robots.txt and terms allow the work, and start with a conservative `requests_per_second`.
4. Run to CSV first and inspect the quality summary and a few rows; tune required fields or selectors.
5. Switch to the Excel output for stakeholder delivery. For client-rendered content, add `mode: javascript` and use the Playwright extra.

The test suite covers parsing, fixture pagination, whitespace/email normalization, validation, deduplication, pipeline quality reporting, and both export formats.
