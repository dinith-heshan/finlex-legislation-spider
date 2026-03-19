#!/usr/bin/env python3

import argparse
import logging
import sys

from typing import Optional

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