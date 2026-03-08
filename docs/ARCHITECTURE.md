# Architecture Overview

## High-Level Pipeline

```
Internet (academic website)
         │
         ▼
┌─────────────────────────────────┐
│  Stage 1 — main_scrape.py       │
│  IntelligentScraper             │
│  + LinkClassifier (AI)          │
│  + APIKeyManager (rotation)     │
└────────────┬────────────────────┘
             │  data/scraped_links.json
             │  data/unique_course_urls.csv
             ▼
┌─────────────────────────────────┐
│  Stage 2 — main_data.py         │
│  course_analyzer.process_url()  │
│  heuristics + AI enrichment     │
└────────────┬────────────────────┘
             │  data/courses_output.csv
             │  (clean → courses_output_cleaned.csv)
             ▼
┌─────────────────────────────────┐
│  Stage 3 — main_generate_       │
│  mdfiles.py                     │
│  markdown_generator             │
│  + LLM material extraction      │
└────────────┬────────────────────┘
             │  data/markdowns/md/<CODE>.md
             ▼
         Docusaurus site
```

---

## Module Dependency Graph

```
main_scrape.py
  └─ utils/scraper.py (IntelligentScraper)
       ├─ utils/link_extractor.py  ← unified anchor extraction
       ├─ utils/link_classifier.py (LinkClassifier)
       │    ├─ utils/api_key_manager.py (APIKeyManager / singleton)
       │    ├─ utils/link_extractor.py
       │    └─ setup/config.py
       └─ setup/config.py

main_data.py
  └─ utils/course_analyzer.py
       ├─ utils/api_key_manager.py
       └─ setup/config.py

main_generate_mdfiles.py
  └─ utils/markdown_generator.py
       ├─ utils/course_analyzer.py (fetch_html, _call_nvidia_api, _parse_ai_json)
       └─ setup/config.py
```

---

## Key Classes and Functions

### `IntelligentScraper` (`utils/scraper.py`)

Orchestrates the entire Stage 1 crawl.

**State held per instance:**
- `visited_urls` — set of already-crawled URLs (prevents loops)
- `course_pages` — confirmed individual course pages
- `course_relevant_links` — catalogs/listings that may contain course pages
- `back_links`, `irrelevant_links`, `file_links`, `inaccessible_links` — classified buckets
- `external_links`, `all_extracted_links` — full extraction record
- `_seen_*` sets — per-bucket dedup (normalized URLs)
- `_fetch_errors` — records error messages for inaccessible URLs

**Recursion strategy:**
- Only `course_relevant_links` are followed recursively (up to `max_depth`)
- `course_pages` are end goals — never recursed into
- `back_links` and `irrelevant_links` are discarded

**Link extraction (`extract_all_links`):**
Extracts from: `<a>`, `<link>`, `<img>`, `<iframe>`, `<area>`, `<form>`, `<base>`, `<video>`, `<audio>`, `<source>`, `<embed>`, `<object>`

---

### `LinkClassifier` (`utils/link_classifier.py`)

AI-powered batch link classification with persistent caching.

**Cache system:**
- Loaded from / saved to `data/link_classification_cache.json` on every new result
- Cache key = normalized URL (lowercase, no fragment)
- Cache-hit links skip AI entirely; only cache-miss links consume API credits

**Batch flow:**
1. Check all links against cache
2. Send only uncached links to NVIDIA API in batches of `BATCH_SIZE`
3. Each batch is retried up to `BATCH_MAX_RETRIES` times on timeout
4. Results stored in cache immediately after each successful batch

**Classification schema (per link):**
```json
{
  "is_back_link":       true/false,
  "is_course_page":     true/false,
  "is_course_relevant": true/false,
  "confidence":         0.0–1.0,
  "reasoning":          "short explanation"
}
```

---

### `extract_links_from_html` (`utils/link_extractor.py`)

Single source of truth for anchor `<a>` link extraction. Enforces 8 rules:

1. Only `<a href="...">` tags
2. Skip empty/whitespace hrefs
3. Skip `#fragment`-only hrefs
4. Skip `javascript:`, `mailto:`, `tel:`, `ftp:`, `data:`, `blob:`
5. Resolve relative URLs via `urljoin`
6. Keep only `http`/`https`
7. Detect and flag file links (PDF, images, etc.); always keep web-page extensions
8. Deduplicate (scheme-normalized + trailing-slash stripped)

---

### `APIKeyManager` (`utils/api_key_manager.py`)

Thread-safe NVIDIA API key rotation.

- Uses `collections.deque` for O(1) rotation
- Singleton pattern via `get_key_manager()` — one instance per process
- Per-key usage counters and error counters
- `remove_key()` removes a bad key permanently from rotation

---

### `process_url` (`utils/course_analyzer.py`)

4-step per-URL pipeline for Stage 2:

| Step | Function | Description |
|---|---|---|
| 1 | `fetch_html(url)` | GET with retry (up to 3 attempts) |
| 2 | `extract_manual_fields(url, html, soup)` | Heuristic extraction: code, title, semester, year, files, internal links |
| 3 | `classify_manual_page_type(extracted, html)` | Rule-based classification (6 types, no AI) |
| 4 | `ai_enrich_page(extracted, html)` → `merge_results()` | LLM enrichment + conflict detection |

**Output dict keys:** `url`, `course_code`, `course_title`, `semester`, `year`, `manual_page_type`, `ai_page_type`, `ai_confidence`, `ai_reasoning`, `has_notes`, `notes_type`, `notes_details`, `further_course_related_data_present`, `has_syllabus_or_logistics`, `is_useful`, `conflict_flag`, `recheck_needed`, `all_files_json`, `all_internal_links_json`

---

### `process_groups` (`utils/markdown_generator.py`)

Orchestrates Stage 3:

1. `load_grouped_links(path)` — groups CSV rows by `course_code`, then `course_title`, then singletons. Sorts each group by year (newest first).
2. For each group:
   - Build an `index_list` (one entry per URL with metadata)
   - For each URL: fetch HTML → heuristic extraction → optional LLM extraction
   - `build_markdown(group_key, index_list, special_marks, per_link_items)` → Docusaurus Markdown string
   - Write to `<output_dir>/<safe_filename>.md`
3. Write `summary.json`

---

## Data File Formats

### `data/link_classification_cache.json`
```json
{
  "https://example.edu/cs101": {
    "is_back_link": false,
    "is_course_page": true,
    "is_course_relevant": false,
    "confidence": 0.95,
    "reasoning": "..."
  }
}
```

### `data/unique_course_urls.csv`
Minimal CSV with at least a `url` column — feed into Stage 2.

### `data/courses_output.csv`
Full analysis output — see `utils/course_analyzer.CSV_COLUMNS` for the complete column list.

### `data/markdowns/md/<CODE>.md`
Docusaurus-compatible Markdown with YAML frontmatter (`title`, `course_code`, `course_title`).

---

## Prompt Files (`prompts/`)

| File | Used by | Purpose |
|---|---|---|
| `sys.txt` | `LinkClassifier` | System prompt for Stage 1 link classification |
| `course_page_analysis.txt` | `course_analyzer` | Prompt template for Stage 2 AI enrichment |
| `markdown_extraction.txt` | `markdown_generator` | Prompt template for Stage 3 material extraction |
| `content_analysis.txt` | `LinkClassifier` (optional) | Prompt for `--verify-content` content verification pass |

All prompts use plain `{placeholder}` substitution (not Python f-string syntax) so JSON examples inside the templates do not need brace-escaping.

---

## Thread Safety

- `APIKeyManager` uses `threading.Lock` for all key accesses
- `IntelligentScraper` is not thread-safe — designed for single-threaded sequential crawling
- The classification cache (`dict`) is not guarded by a lock — do not share `LinkClassifier` instances across threads

---

## Error Handling Strategy

| Layer | Failure | Recovery |
|---|---|---|
| HTTP fetch | `requests.RequestException` | Retry up to `max_retries`; record in `inaccessible_links` |
| Batch API call | Timeout | Exponential-backoff retry up to `BATCH_MAX_RETRIES` |
| Batch API call | Non-timeout error | Log, return conservative fallback (all False) |
| JSON parsing | Malformed response | Strip markdown fences, greedy regex match; fallback to `_AI_FALLBACK` dict |
| AI enrichment (Stage 2) | Any exception | Return `_AI_FALLBACK` dict; set `conflict_flag=True`, `recheck_needed=True` |
| Keyboard interrupt (Stage 1) | `KeyboardInterrupt` | Save current progress then exit |
