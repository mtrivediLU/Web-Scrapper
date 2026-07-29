"""Responsible HTTP fetching with rate limits, retries, and robots.txt checks."""

from __future__ import annotations

import logging
import time
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import httpx

from web_scraper.config import ScrapeConfig

LOGGER = logging.getLogger(__name__)


class Fetcher:
    """Fetch URLs conservatively; fixture URLs make demonstrations deterministic."""

    def __init__(self, config: ScrapeConfig) -> None:
        self.config = config
        self.client = httpx.Client(
            timeout=config.timeout_seconds,
            follow_redirects=True,
            headers={"User-Agent": config.user_agent, "Accept": "text/html,application/json"},
        )
        self._last_request = 0.0
        self._robots: dict[str, RobotFileParser] = {}

    def close(self) -> None:
        self.client.close()

    def __enter__(self) -> Fetcher:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def resolve_url(self, base_url: str, value: str) -> str:
        if value.startswith(("http://", "https://", "fixture://")):
            return value
        if base_url.startswith("fixture://"):
            prefix = base_url.rsplit("/", 1)[0]
            return f"{prefix}/{value.lstrip('/')}"
        return urljoin(base_url, value)

    def get_text(self, url: str) -> str:
        if url.startswith("fixture://"):
            return self._read_fixture(url)
        self.prepare_request(url)
        for attempt in range(self.config.retries + 1):
            try:
                response = self.client.get(url)
                response.raise_for_status()
                return response.text
            except (httpx.HTTPError, httpx.TimeoutException) as error:
                if attempt == self.config.retries:
                    raise RuntimeError(f"Request failed after retries: {url}") from error
                delay = 2**attempt
                LOGGER.warning("Request failed for %s; retrying in %ss: %s", url, delay, error)
                time.sleep(delay)
        raise AssertionError("unreachable")

    def prepare_request(self, url: str) -> None:
        """Apply safeguards before a non-HTTPX requester, such as Playwright, navigates."""
        if not url.startswith("fixture://"):
            self._check_robots(url)
            self._rate_limit()

    def _read_fixture(self, url: str) -> str:
        if self.config.fixture_dir is None:
            raise ValueError("fixture:// URLs require fixture_dir in the configuration")
        relative = url.removeprefix("fixture://")
        path = (self.config.fixture_dir / relative).resolve()
        if self.config.fixture_dir not in path.parents:
            raise ValueError("Fixture path escapes fixture_dir")
        return path.read_text(encoding="utf-8")

    def _rate_limit(self) -> None:
        if self.config.requests_per_second <= 0:
            return
        interval = 1 / self.config.requests_per_second
        remaining = interval - (time.monotonic() - self._last_request)
        if remaining > 0:
            time.sleep(remaining)
        self._last_request = time.monotonic()

    def _check_robots(self, url: str) -> None:
        if not self.config.respect_robots_txt:
            return
        parsed = urlparse(url)
        origin = f"{parsed.scheme}://{parsed.netloc}"
        parser = self._robots.get(origin)
        if parser is None:
            robots_url = urljoin(origin, "/robots.txt")
            parser = RobotFileParser(robots_url)
            try:
                response = self.client.get(robots_url, timeout=self.config.timeout_seconds)
                parser.parse(response.text.splitlines() if response.is_success else [])
            except httpx.HTTPError as error:
                LOGGER.warning("Could not read robots.txt for %s: %s", origin, error)
                parser.parse([])
            self._robots[origin] = parser
        if not parser.can_fetch(self.config.user_agent, url):
            raise PermissionError(f"robots.txt disallows scraping {url}")
