# Pipeline Guide

End-to-end walkthrough for running all three stages of the pipeline.

---

## Prerequisites

- Python 3.13+
- NVIDIA API key (free at https://build.nvidia.com/)
- `.env` file with `NVIDIA_API_KEY=nvapi-...`

---

## Stage 1 — Scrape (`main_scrape.py`)

### What it does

Starts at a base URL and recursively crawls the website. For each page, it extracts all links (anchors, images, iframes, media, forms, etc.) and uses an AI model to classify each same-domain link into one of four buckets:

| Bucket | Meaning | Recursed into? |
|---|---|---|
| `course_pages` | Individual course pages (CS101, etc.) | No — end goal |
| `course_relevant_links` | Catalogs, listings, faculty pages | Yes — may contain course pages |
| `back_links` | Navigation, home, parent pages | No |
| `irrelevant_links` | Unrelated content | No |

File links (PDFs, images, etc.) are stored separately in `file_links` and not recursed into.

### Running

```bash
# Default: IIT KGP CSE faculty page, depth 7
python main_scrape.py

# Quick test — limit depth
python main_scrape.py --depth 2

# Custom site
python main_scrape.py --url "https://your-university.edu/faculty" --depth 3

# Save progress checkpoint every 50 links (useful for large crawls)
python main_scrape.py --save-interval 50

# Enable optional 2nd AI pass to verify each course page's HTML content
python main_scrape.py --verify-content

# Skip AI entirely (faster; collects all links without classification)
python main_scrape.py --no-ai --output data/all_links.json
```

### Output: `data/scraped_links.json`

Key fields:
- `course_pages` — list of confirmed course page objects (url, text, confidence, reasoning)
- `course_relevant_links` — links to pages that may contain more course pages
- `file_links` — PDFs, slides, images found during crawl
- `inaccessible_links` — 403/timeout URLs with error messages
- `stats` — counts for all buckets

### Extracting course URLs for Stage 2

After Stage 1, extract the course page URLs and save as a CSV:

```python
import json, csv

with open("data/scraped_links.json") as f:
    data = json.load(f)

with open("data/unique_course_urls.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=["url"])
    writer.writeheader()
    seen = set()
    for link in data["course_pages"]:
        url = link["url"]
        if url not in seen:
            seen.add(url)
            writer.writerow({"url": url})

print(f"Saved {len(seen)} unique course URLs")
```

---

## Stage 2 — Analyze (`main_data.py`)

### What it does

Reads `data/unique_course_urls.csv` and processes each URL through a 4-step pipeline:

1. **Fetch HTML** (with retry)
2. **Heuristic extraction** — course code, title, semester, year, downloadable files, internal links
3. **Rule-based classification** — assigns one of 6 page type labels without AI
4. **AI enrichment** — sends HTML snippet + extracted fields to `meta/llama-3.1-70b-instruct` for deep analysis

### Running

```bash
python main_data.py
```

No command-line arguments — configure paths in `utils/course_analyzer.py` (`INPUT_CSV`, `OUTPUT_CSV`).

### Output: `data/courses_output.csv`

Columns include: `url`, `course_code`, `course_title`, `semester`, `year`, `manual_page_type`, `ai_page_type`, `ai_confidence`, `has_notes`, `is_useful`, `conflict_flag`, `recheck_needed`, `all_files_json`, …

### Cleaning the output

Before running Stage 3, deduplicate and normalize the CSV:

```bash
# Uses union-find to merge rows with same course_code or course_title
python utils/clean_courses.py
```

This writes the cleaned data to `data/courses_output_cleaned.csv` (or the path set in the script). Stage 3 reads this file.

Alternatively, open `data/courses_output.csv` in a spreadsheet editor and:
- Remove duplicate course codes
- Merge rows for the same course from different years (keep all URLs — Stage 3 groups them)
- Flag `recheck_needed=True` rows for manual inspection

---

## Stage 3 — Generate Markdown (`main_generate_mdfiles.py`)

### What it does

Reads the cleaned CSV and generates one Markdown file per course. Rows are grouped by `course_code` first, then by `course_title`, then as singletons. Within each group, URLs are sorted newest-first by year.

For each URL in a group, it:
1. Fetches the page HTML
2. Extracts learning materials using heuristics (regex on links and text)
3. Optionally sends HTML to `meta/llama-3.1-70b-instruct` for deeper extraction
4. Builds a Docusaurus-compatible Markdown document

### Running

```bash
# Full run (default input: data/courses_output_cleaned.csv)
python main_generate_mdfiles.py

# Test mode — only process 3 groups
python main_generate_mdfiles.py --test

# Limit to first N groups
python main_generate_mdfiles.py --limit 10

# Skip LLM calls (heuristics only — faster, fewer API calls)
python main_generate_mdfiles.py --no-llm

# See what groups would be processed without making any changes
python main_generate_mdfiles.py --dry-run

# Custom input/output
python main_generate_mdfiles.py \
  --input data/courses_output_cleaned.csv \
  --output data/markdowns/md
```

### Output

- `data/markdowns/md/<COURSE_CODE>.md` — one file per course group
- `data/markdowns/md/summary.json` — processed count, failed URLs

### Markdown format

```markdown
---
title: "Algorithms — CS20003"
course_code: "CS20003"
course_title: "Algorithms"
---

# Algorithms — CS20003

## Autumn 2024
**Source**: [https://...](https://...)

### Lecture Slides
- [Lecture 1: Introduction](https://...)
- [Lecture 3: Sorting](https://...)

### Question Papers
- [Mid Sem 2024](https://...)
- [End Sem 2023](https://...)

### Tutorials & Assignments
- [Assignment 1](https://...)
```

---

## Full Run Checklist

```
[ ] 1. cp template.env .env  →  add NVIDIA_API_KEY
[ ] 2. pip install -r requirements.txt
[ ] 3. python main_scrape.py --depth 3          # Stage 1
[ ] 4. Extract course URLs → data/unique_course_urls.csv
[ ] 5. python main_data.py                      # Stage 2
[ ] 6. python utils/clean_courses.py            # Clean CSV
[ ] 7. python main_generate_mdfiles.py          # Stage 3
[ ] 8. Check data/markdowns/md/ for output files
```

---

## Tips for Large Crawls

- **Use multiple API keys** — add `NVIDIA_API_KEY_1`, `NVIDIA_API_KEY_2`, etc. to `.env` for proportionally higher throughput
- **Checkpoint saves** — Stage 1 saves periodically every `--save-interval` links (default: 200). Interrupt safely with Ctrl+C; progress is saved.
- **Classification cache** — Stage 1 caches every AI result in `data/link_classification_cache.json`. Re-running on the same site is free (no API calls for already-seen URLs).
- **Start shallow** — use `--depth 2` first to verify the scraper finds course pages, then increase depth.
- **Dry run Stage 3** — `python main_generate_mdfiles.py --dry-run` lists all course groups before committing API calls.
- **Heuristics-only pass** — `python main_generate_mdfiles.py --no-llm` is useful for a quick preview without API costs.

---

## Adapting to a Different University

1. **Change the base URL** in `main_scrape.py` or pass `--url`:
   ```bash
   python main_scrape.py --url "https://cs.mit.edu/faculty" --depth 3
   ```

2. **Tune the system prompt** in `prompts/sys.txt` — define what counts as a "course page" for your domain.

3. **Tune `prompts/course_page_analysis.txt`** — adjust the JSON schema expected from Stage 2 AI enrichment.

4. **Adjust heuristic patterns** in `utils/course_analyzer.py`:
   - `_SYLLABUS_KW`, `_LOGISTICS_KW`, `_NOTES_KW` regex patterns
   - `_MANUAL_TO_AI` mapping

5. **Adjust `utils/link_extractor.py`** `FILE_EXTENSIONS` if the site uses unusual file types.
