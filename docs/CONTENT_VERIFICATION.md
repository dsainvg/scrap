# Content Verification Feature

## Overview

Content verification is an **optional second AI pass** in Stage 1 (`main_scrape.py`). After the AI link classifier identifies a page as a potential course page, the verifier fetches the page's HTML and sends it to a second LLM call to confirm and extract metadata.

It is disabled by default because it roughly doubles API usage for each identified course page.

---

## How It Works

### Normal flow (without `--verify-content`)

```
URL → [Link Classifier] → is_course_page=True → stored in course_pages
```

### With `--verify-content`

```
URL → [Link Classifier] → is_course_page=True
                                    ↓
                    [Content Verifier: fetch HTML + AI]
                                    ↓
              confidence > 0.5?  Yes → stored in course_pages (with metadata)
                                  No  → moved to course_relevant_links
```

---

## Usage

```bash
# Enable content verification
python main_scrape.py --verify-content

# Combined with other options
python main_scrape.py \
  --url "https://cse.iitkgp.ac.in/faculty4.php" \
  --depth 2 \
  --verify-content \
  --save-interval 50
```

### Programmatic usage

```python
from utils.scraper import IntelligentScraper

scraper = IntelligentScraper(
    base_url="https://example.edu/",
    use_ai_classification=True,
    verify_course_content=True,
)
results = scraper.scrape(max_depth=2)
```

---

## What the Verifier Checks

The content analyzer looks for:

- Course code/number (e.g., `CS20003`, `MATH-202`)
- Course title
- Syllabus or course outline
- Lecture schedule with topics/dates
- Assignments, homework, projects
- Course materials (slides, notes)
- Grading policy, office hours, prerequisites
- Semester/year information
- Links to other course pages embedded in content

---

## Output — Enhanced Course Page Objects

When content verification succeeds, course page entries in `data/scraped_links.json` include extra fields:

```json
{
  "url": "https://example.edu/~faculty/CS101/",
  "text": "CS 101 - Algorithms",
  "is_course_page": true,
  "confidence": 0.95,
  "content_verified": true,
  "verification_confidence": 0.95,
  "verified_course_code": "CS101",
  "verified_course_name": "Introduction to Algorithms",
  "verified_semester": "Autumn 2024"
}
```

---

## Model Used

Content verification uses `CONTENT_VERIFICATION_MODEL` from `setup/config.py`:

```python
CONTENT_VERIFICATION_MODEL = "meta/llama-3.1-70b-instruct"
```

This is the same model used by Stage 2 (`main_data.py`) and Stage 3 (`main_generate_mdfiles.py`).

---

## API Cost Impact

| Mode | API calls (approx.) |
|---|---|
| Without `--verify-content` | ~1 call per `BATCH_SIZE` links |
| With `--verify-content` | +1 call per identified course page |

**Recommendation:** Run without `--verify-content` first to discover course pages. Use `--verify-content` for a final, accuracy-critical pass.

---

## Prompt

The verification prompt lives in `prompts/content_analysis.txt`. Edit it to adjust what the AI looks for when deciding whether a page is a genuine course page.

---

## When to Use

**Use `--verify-content` when:**
- You need high confidence that identified pages are genuine course pages
- You want course metadata (code, name, semester) attached to results without running Stage 2
- False positives from link classification are a concern

**Skip `--verify-content` when:**
- Running a quick exploratory crawl
- API budget is limited
- Stage 2 (`main_data.py`) will perform deeper analysis anyway

---

## Troubleshooting

**Verification is slow**
- Each page requires an extra HTTP fetch + AI call — this is expected
- Use multiple API keys (`NVIDIA_API_KEY_1`, `_2`, etc.) to increase throughput

**Some pages fail verification**
- Pages that are 403/timeout are recorded in `inaccessible_links`
- Pages with unusual layouts may have low confidence and be reclassified as `course_relevant`

**No additional course links extracted**
- Normal for pages that don't link to other courses
- The verifier only reports links that appear to be course pages themselves

## Architecture

```
┌─────────────────────────────────────────────────┐
│            Intelligent Scraper                   │
└─────────────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────┐
│  Stage 1: Link Classification (Qwen 3.5)        │
│  - Analyze URL & context                         │
│  - Classify links                                │
└─────────────────────────────────────────────────┘
                      │
                      ▼
              Is course page?
                      │
                      ▼ Yes (if enabled)
┌─────────────────────────────────────────────────┐
│  Stage 2: Content Verification (Llama 3.1)     │
│  - Fetch page content                            │
│  - Verify course page                            │
│  - Extract metadata                              │
│  - Find course links                             │
└─────────────────────────────────────────────────┘
                      │
                      ▼
              Verified course page +
              Extracted course links
```
