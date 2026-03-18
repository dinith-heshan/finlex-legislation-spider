# Finlex Legislation Spider

A pure-HTTP Python spider that scrapes Finnish legislation from
[Finlex](https://www.finlex.fi/en/legislation) for a target year and
produces structured metadata, cleaned HTML, and sentence-aware text chunks
per document.

---

## Quick start

```bash
# 1. Create a virtual environment
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run (defaults to year 2026)
python spider.py --year 2026 --output ./output

# Dry-run with only 5 documents
python spider.py --year 2026 --output ./output --limit 5

# Run unit tests
python spider.py --test
```

All arguments:

| Flag | Default | Description |
|---|---|---|
| `--year` | `2026` | Target legislation year |
| `--output` | `./output` | Output directory |
| `--delay` | `1.5` | Base pause between HTTP requests (seconds) |
| `--max-retries` | `4` | Retry attempts per request (exponential back-off) |
| `--limit` | *(none)* | Cap number of documents (for testing) |
| `--log-level` | `INFO` | `DEBUG`, `INFO`, `WARNING`, or `ERROR` |
| `--test` | — | Run unit tests and exit |

---

## Output layout

```
output/
├── metadata.json          # Array of all metadata objects
├── cleaned/
│   ├── 2026_0001.html     # Cleaned HTML per statute
│   ├── 2026_0002.html
│   └── …
└── chunks/
    ├── 2026_0001_chunk_001.txt
    ├── 2026_0001_chunk_002.txt
    └── …
```

File names encode the year and the zero-padded statute serial number
extracted from the URL (`/en/legislation/YEAR/SERIAL`).

---

## Design decisions

### 1. Next.js awareness

Finlex is a Next.js application.  Every page includes a
`<script id="__NEXT_DATA__">` tag containing the full server-rendered
JSON payload.  The spider:

1. Parses that JSON to extract legislation links and metadata fields
   (more reliable than scraping rendered HTML).
2. Constructs the `/_next/data/{buildId}/…json` URL for each page,
   which returns pure JSON without any HTML rendering noise — used as a
   faster, more structured alternative to HTML parsing.
3. Falls back transparently to BeautifulSoup HTML parsing when either
   mechanism is unavailable or returns nothing.

### 2. Discovery strategy

Starting from `/en/legislation`, the spider:

* Finds the sidebar year-filter link for the target year (or falls back
  to the canonical `/en/legislation/{year}` URL).
* Collects all `/en/legislation/{year}/{serial}` links from each listing
  page, following pagination links (`rel="next"`, `aria-label`, page-query
  parameters) until no next page is found.

> **Limitation**: if the year listing uses infinite scroll / JS-only
> pagination, only the server-rendered first page is discoverable without
> browser automation.  All discovered URLs are logged so you can verify
> completeness.

### 3. Metadata extraction

Fields are extracted in this priority order:

1. `__NEXT_DATA__` JSON payload (deepest / most structured source).
2. `/_next/data/…json` endpoint data.
3. HTML `<dl>` / `<table>` blocks (fallback for older or simpler pages).

`statute_number` is always inferred from the URL (`/legislation/YEAR/SERIAL`
→ `SERIAL/YEAR`) if not found explicitly.

`translation_available` is set to `false` when the page text contains any
of the known "translation not yet available" phrases (in English or Finnish).

### 4. HTML cleaning

The cleaner:

* Removes `<nav>`, `<header>`, `<footer>`, `<aside>`, `<script>`,
  `<style>`, `<noscript>`, `<iframe>`, `<form>` and all their children.
* Strips elements whose `class` or `id` matches a boilerplate pattern
  (navigation, breadcrumbs, cookie banners, ads, social share bars, etc.).
* Locates the main content container via `<main>`, `[role="main"]`,
  `<article>`, or common CSS selectors, then falls back to `<body>`.
* Keeps only semantic tags: `h1–h6`, `p`, `ul/ol/li`, `table/*`,
  `blockquote`, `strong`, `em`, `br`, `hr`.
* Strips all element attributes except: `colspan`, `rowspan`, `scope`,
  `href`, `src`, `alt`, `title`, `lang`.
* Produces valid, self-contained HTML5.

### 5. Chunking algorithm

```
document
  └─ sections  (heading + following paragraphs)
       ├─ merge forward if section < 800 chars
       ├─ emit as single chunk if ≤ 1 200 chars
       └─ split at sentence boundaries if > 1 200 chars
```

* **Sentence splitter** uses a regex that avoids false positives on
  abbreviations (`No.`, `Art.`, `Sec.`, `vol.`, `etc.`, single-letter
  abbreviations, decimal numbers).
* **Each chunk** is prefixed with the Markdown heading of its section
  (e.g., `## Section 3 — Definitions\n\n`) so downstream RAG pipelines
  retain context.
* **Target**: 800–1 200 characters; configured via `chunk_document()`
  parameters.

### 6. Throttling & retry

* Base delay of 1.5 s + uniform jitter [0, 0.3 s] between every request.
* On HTTP 429 the back-off starts at `2^3 = 8 s`; on 5xx / network errors
  it starts at `2^0 = 1 s`, doubling each attempt.
* Up to 4 attempts per URL (configurable via `--max-retries`).

### 7. Resumability

`output/.progress.json` stores the set of fully-processed URLs.  Re-running
the spider skips any URL already present in that file.  `metadata.json` is
written after each successfully processed document (checkpoint saves), so
partial runs are never lost.

---

## Running unit tests

```bash
python spider.py --test
```

Tests cover:

* `TestMetadataExtraction` — statute number inference, translation flag,
  title extraction, `<dl>` / `<table>` metadata parsing, language version
  splitting.
* `TestChunking` — empty document, section headers in chunks, no
  mid-sentence splits, short-section merging, long-section splitting,
  chunk size bounds.

---

## Dependencies

| Package | Purpose |
|---|---|
| `requests` | HTTP client |
| `beautifulsoup4` | HTML parsing |
| `lxml` | Fast HTML/XML parser backend for BS4 |
| `html5lib` | Optional fallback parser for malformed HTML |

Only Python standard library beyond that.
