#!/usr/bin/env python3

import argparse
import logging
import random
import re
import requests
import sys
import time

from __future__ import annotations

from bs4 import BeautifulSoup
from typing import Any, Dict, List, Optional

# ── Logging ────────────────────────────────────────────────────────────────────

def _setup_logging(level: str = "INFO") -> None:
    fmt = "%(asctime)s [%(levelname)-8s] %(message)s"
    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]
    try:
        handlers.append(logging.FileHandler("spider.log", encoding="utf-8"))
    except OSError as e:
        logging.warning("File logging failed: %s", e)
    logging.basicConfig(level=getattr(logging, level.upper(), logging.INFO),
                        format=fmt, handlers=handlers)


log = logging.getLogger("finlex")

# ── Constants ──────────────────────────────────────────────────────────────────

BASE_URL        = "https://www.finlex.fi"
LEGISLATION_URL = "https://www.finlex.fi/en/legislation"
DEFAULT_DELAY       = 1.5   # seconds
DEFAULT_MAX_RETRIES = 4
DEFAULT_BACKOFF     = 2.0   # exponential base

_TRANSLATION_ABSENT = [
    "translation is not yet available",
    "not yet been translated",
    "not been translated",
    "translation not available",
    "translation not yet available",
    "has not yet been translated into english",
    "english translation of this legislation is not",
    "ei ole vielä käännetty",
    "käännöstä ei ole",
]

# ── HTTP client ────────────────────────────────────────────────────────────────

class ThrottledSession:
    """requests.Session wrapper with rate limiting and retry logic."""

    def __init__(
        self,
        delay: float       = DEFAULT_DELAY,
        max_retries: int   = DEFAULT_MAX_RETRIES,
        backoff: float     = DEFAULT_BACKOFF,
    ) -> None:
        self.delay       = delay
        self.max_retries = max_retries
        self.backoff     = backoff
        self._last: float = 0.0

        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0 Safari/537.36 "
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
        })

    # ── internal ──────────────────────────────────────────────────────────────

    def _wait(self) -> None:
        gap = time.time() - self._last
        need = self.delay - gap
        if need > 0:
            time.sleep(need + random.uniform(0.0, 0.3))
        self._last = time.time()

    # ── public ────────────────────────────────────────────────────────────────

    def get(self, url: str, **kwargs) -> requests.Response:
        last_exc: Exception = RuntimeError("Unknown error")
        for attempt in range(self.max_retries):
            self._wait()
            try:
                r = self.session.get(url, timeout=30, **kwargs)
                r.raise_for_status()
                return r
            except requests.HTTPError as exc:
                code = exc.response.status_code if exc.response is not None else 0
                wait = self.backoff ** (attempt + (2 if code == 429 else 1))
                log.warning("HTTP %s for %s — retry %d/%d in %.1fs",
                            code, url, attempt + 1, self.max_retries, wait)
                time.sleep(wait)
                last_exc = exc
            except (requests.ConnectionError, requests.Timeout) as exc:
                wait = self.backoff ** attempt
                log.warning("Network error (%s) — retry %d/%d in %.1fs",
                            exc, attempt + 1, self.max_retries, wait)
                time.sleep(wait)
                last_exc = exc
        raise RuntimeError(f"Failed to GET {url} after {self.max_retries} attempts") from last_exc


# ── Discovery ──────────────────────────────────────────────────────────────────

class LegislationDiscovery:
    """Finds all individual legislation URLs for a given year."""

    def __init__(self, session: ThrottledSession, year: int) -> None:
        self.session = session
        self.year    = year
        self._url_re = re.compile(
            rf"(?:^|/)en/legislation/{year}/(\d+)(?:[?#].*)?$"
        )

    # ── link extraction ───────────────────────────────────────────────────────

    def _links_from_next_data(self, data: Dict) -> List[str]:
        urls: List[str] = []
        seen: set = set()

        def _check(val: Any) -> bool:
            return isinstance(val, str) and self._url_re.search(val) is not None

        for raw in _deep_find(data, _check):
            full = urljoin(BASE_URL, raw) if not raw.startswith("http") else raw
            if full not in seen:
                seen.add(full)
                urls.append(full)
        return urls

    def _links_from_html(self, soup: BeautifulSoup) -> List[str]:
        urls: List[str] = []
        seen: set = set()
        for a in soup.find_all("a", href=True):
            href: str = a["href"]
            if self._url_re.search(href):
                full = urljoin(BASE_URL, href)
                if full not in seen:
                    seen.add(full)
                    urls.append(full)
        return urls

    def _links_from_page(self, soup: BeautifulSoup) -> List[str]:
        data = _next_data(soup)
        if data:
            found = self._links_from_next_data(data)
            if found:
                log.debug("  %d links from __NEXT_DATA__", len(found))
                return found
        found = self._links_from_html(soup)
        log.debug("  %d links from HTML", len(found))
        return found

    # ── year URL discovery ────────────────────────────────────────────────────

    def _year_url(self, soup: BeautifulSoup) -> str:
        """Return the URL for the given year's legislation listing."""
        year_str = str(self.year)
        for a in soup.find_all("a", href=True):
            href: str = a["href"]
            text = a.get_text(strip=True)
            if text == year_str or (year_str in href and "/legislation" in href):
                return urljoin(BASE_URL, href)
        # Canonical fallback
        return f"{LEGISLATION_URL}/{self.year}"

    # ── next-page discovery ───────────────────────────────────────────────────

    def _next_page_url(self, soup: BeautifulSoup, current_url: str) -> Optional[str]:
        """Return next-page URL if pagination is present, else None."""
        # Rel-next link tag
        rel = soup.find("link", rel="next")
        if rel and rel.get("href"):
            return urljoin(current_url, rel["href"])

        # <a> with obvious "next" semantics
        next_re = re.compile(r"^(next|→|>|»|›)$", re.I)
        for a in soup.find_all("a", href=True):
            txt   = a.get_text(strip=True)
            aria  = a.get("aria-label", "")
            rel_a = a.get("rel", [])
            if (next_re.match(txt) or "next" in aria.lower()
                    or "next" in [r.lower() for r in rel_a]):
                candidate = urljoin(current_url, a["href"])
                if candidate != current_url:
                    return candidate

        # Check __NEXT_DATA__ for pagination metadata
        data = _next_data(soup)
        if data:
            def _is_page_url(v: Any) -> bool:
                return (isinstance(v, str)
                        and f"/legislation/{self.year}" in v
                        and "page=" in v)
            pages = _deep_find(data, _is_page_url)
            parsed_current = urlparse(current_url)
            current_page = int(
                re.search(r"page=(\d+)", parsed_current.query or "").group(1)
                if "page=" in (parsed_current.query or "") else "1"
            )
            for p in pages:
                m = re.search(r"page=(\d+)", p)
                if m and int(m.group(1)) == current_page + 1:
                    return urljoin(BASE_URL, p)

        return None

    # ── Try Next.js JSON data endpoint ────────────────────────────────────────

    def _try_nextjs_json(self, build_id: str, url: str) -> Optional[Dict]:
        """Try the /_next/data/{buildId}/… endpoint."""
        parsed = urlparse(url)
        path   = parsed.path.rstrip("/") + ".json"
        json_url = f"{BASE_URL}/_next/data/{build_id}{path}"
        return self.session.get_json(json_url)

    # ── public entry point ────────────────────────────────────────────────────

    def discover(self) -> List[str]:
        log.info("── Discovery: year %d ──────────────────────────────────────", self.year)

        # 1. Load main listing page
        log.info("Fetching %s", LEGISLATION_URL)
        r    = self.session.get(LEGISLATION_URL)
        soup = BeautifulSoup(r.text, "lxml")
        bid  = _build_id(soup)
        if bid:
            log.debug("Next.js buildId: %s", bid)

        # 2. Locate the year-specific listing URL
        year_url = self._year_url(soup)
        log.info("Year listing URL: %s", year_url)

        all_urls: List[str] = []
        seen: set  = set()
        page_url: Optional[str] = year_url
        page_num = 1

        while page_url:
            log.info("  Listing page %d: %s", page_num, page_url)

            # Try Next.js JSON shortcut first
            page_soup: Optional[BeautifulSoup] = None
            if bid:
                jdata = self._try_nextjs_json(bid, page_url)
                if jdata:
                    links = self._links_from_next_data(jdata)
                    if links:
                        log.debug("  JSON shortcut yielded %d links", len(links))
                        for u in links:
                            if u not in seen:
                                seen.add(u)
                                all_urls.append(u)
                        # Still need soup to find next-page link
                        r2 = self.session.get(page_url)
                        page_soup = BeautifulSoup(r2.text, "lxml")
                        page_url = self._next_page_url(page_soup, page_url)
                        page_num += 1
                        continue

            # Fall back to HTML parsing
            if page_soup is None:
                rv = self.session.get(page_url)
                page_soup = BeautifulSoup(rv.text, "lxml")

            links = self._links_from_page(page_soup)
            log.info("  %d item(s) found on page %d", len(links), page_num)

            for u in links:
                if u not in seen:
                    seen.add(u)
                    all_urls.append(u)

            page_url = self._next_page_url(page_soup, page_url)
            page_num += 1

        log.info("Discovery complete — %d unique legislation URLs", len(all_urls))
        return all_urls


# ── Spider ─────────────────────────────────────────────────────────────────────

class FinlexSpider:
    """Orchestrates discovery → scraping → output."""

    def __init__(
        self,
        year:        int   = 2026,
        output_dir:  str   = "./output",
        delay:       float = DEFAULT_DELAY,
        max_retries: int   = DEFAULT_MAX_RETRIES,
        limit:       Optional[int] = None,
    ) -> None:
        self.year    = year
        self.limit   = limit
        self.session = ThrottledSession(delay=delay, max_retries=max_retries)
        self.disc    = LegislationDiscovery(self.session, year)


# ── CLI ────────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Finlex Legislation Spider — scrapes Finnish legislation",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--year",        type=int,   default=2026,
                        help="Target legislation year")
    parser.add_argument("--output",      default="./output",
                        help="Output directory")
    parser.add_argument("--delay",       type=float, default=DEFAULT_DELAY,
                        help="Base delay between requests (seconds)")
    parser.add_argument("--max-retries", type=int,   default=DEFAULT_MAX_RETRIES,
                        help="Max retry attempts per request")
    parser.add_argument("--limit",       type=int,   default=None,
                        help="Limit number of documents (useful for testing)")
    parser.add_argument("--log-level",   default="INFO",
                        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                        help="Logging verbosity")
    parser.add_argument("--test",        action="store_true",
                        help="Run unit tests and exit")

    args = parser.parse_args()

    # Re-configure logging with chosen level
    _setup_logging(args.log_level)
    log.info("Logger configured")

    FinlexSpider(
        year        = args.year,
        output_dir  = args.output,
        delay       = args.delay,
        max_retries = args.max_retries,
        limit       = args.limit,
    )


if __name__ == "__main__":
    main()

# python spider.py --year 2026 --output ./output