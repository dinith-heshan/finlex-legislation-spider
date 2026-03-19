#!/usr/bin/env python3

import argparse

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


if __name__ == "__main__":
    main()

# python spider.py --year 2026 --output ./output