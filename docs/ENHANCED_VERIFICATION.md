# Enhanced Content Verification Features

## Overview

The content verification system has been enhanced with intelligent link extraction and reclassification capabilities. This allows the scraper to:

1. **Detect pages containing course links** even if the page itself isn't a course page
2. **Extract and batch classify** links found within verified pages
3. **Automatically reclassify** misclassified pages based on their content
4. **Discover more courses** by following links extracted from verified pages

---

## New Features

### 1. has_other_course_links Detection

A new boolean flag that indicates whether a page contains links to other course pages.

**Purpose:**
- Identifies pages that should be further explored
- Helps distinguish between terminal course pages and gateway pages
- Enables smarter reclassification decisions

**Examples:**
- Professor's teaching page listing courses → `has_other_course_links: true`
- Course catalog or index → `has_other_course_links: true`  
- Single course page with no other course links → `has_other_course_links: false`

### 2. Automatic Reclassification

Pages that fail course page verification but contain course links are automatically reclassified.

**Logic:**
```
IF page is NOT a course page
  AND has_other_course_links is true
  AND course_links_found is not empty
THEN
  → Reclassify as "course_relevant"
  → Add to scraping queue for further exploration
  → Extract links for batch classification
```

**Benefits:**
- Prevents loss of valuable gateway pages
- Ensures pages with course links are explored
- Reduces false negatives from initial classification

### 3. Link Extraction & Batch Classification

Extracted links from verified pages are sent for batch classification.

**Workflow:**
```
1. Verify course page content
2. Extract course links from HTML
3. Collect all extracted links
4. Batch classify using filter_links()
5. Add newly discovered course pages to results
6. Add course_relevant links to queue
```

**Benefits:**
- Discovers courses that weren't in initial crawl
- Leverages existing batch classification logic
- Efficient API usage through batching

---

## How It Works

### Stage 1: Initial Classification
```
Link → AI Classification → Categorized as "course_page"
```

### Stage 2: Content Verification (if enabled)
```
Course Page Candidate
  ↓
Fetch & Analyze Content
  ↓
AI Content Analysis
  ↓
Returns:
  - is_course_page: bool
  - has_other_course_links: bool
  - course_links_found: [...]
```

### Stage 3: Decision Logic

#### Scenario A: Verified Course Page
```
is_course_page = true
has_other_course_links = true
  ↓
✓ Keep as course_page
→ Extract course_links_found
→ Batch classify extracted links
→ Add new discoveries to results
```

#### Scenario B: Not a Course Page, But Has Course Links
```
is_course_page = false
has_other_course_links = true
course_links_found = [...]
  ↓
↻ Reclassify as "course_relevant"
→ Add to scraping queue
→ Extract course_links_found
→ Batch classify extracted links
→ Scraper will recurse into this page
```

#### Scenario C: Not a Course Page, No Links
```
is_course_page = false
has_other_course_links = false
  ↓
✗ Verification failed
→ Marked as failed verification
→ Not added to results
```

---

## Configuration

### Enable Content Verification

```bash
python main.py --verify-content
```

### Prompt Configuration

The content analysis prompt is in: `prompts/content_analysis.txt`

Key sections for link extraction:
- **Extracting Course Links** - Instructions for finding course links
- **has_other_course_links** - When to set this flag
- **Response Format** - Required JSON structure

### Rate Limiting

Automatic rate limiting is included:
- 0.5 second delay between content verification requests
- Prevents API throttling
- Configurable in scraper code

---

## Response Format

### Enhanced Verification Result

```json
{
    "is_course_page": true,
    "confidence": 0.95,
    "course_code": "CS101",
    "course_name": "Introduction to Programming",
    "semester": "Fall 2024",
    "reasoning": "Contains syllabus, assignments, course schedule",
    "has_other_course_links": true,
    "course_links_found": [
        {
            "url": "https://example.edu/courses/CS102.html",
            "text": "CS 102: Data Structures",
            "likely_course_code": "CS102"
        },
        {
            "url": "https://example.edu/courses/CS201.html",
            "text": "CS 201: Algorithms",
            "likely_course_code": "CS201"
        }
    ]
}
```

---

## Example Scenarios

### Example 1: Faculty Teaching Page

**Page Type:** Not a course page itself, but lists multiple courses

**URL:** `https://university.edu/~prof/teaching.html`

**Content Analysis Result:**
```json
{
    "is_course_page": false,
    "confidence": 0.2,
    "has_other_course_links": true,
    "course_links_found": [
        {"url": "...CS101.html", "text": "CS 101"},
        {"url": "...CS102.html", "text": "CS 102"},
        {"url": "...CS201.html", "text": "CS 201"}
    ]
}
```

**What Happens:**
1. ↻ Reclassified as "course_relevant"
2. → Added to scraping queue
3. → 3 links extracted and batch classified
4. ✓ New course pages discovered

### Example 2: Verified Course Page with Related Courses

**Page Type:** Actual course page

**URL:** `https://university.edu/courses/CS101.html`

**Content Analysis Result:**
```json
{
    "is_course_page": true,
    "confidence": 0.95,
    "course_code": "CS101",
    "has_other_course_links": true,
    "course_links_found": [
        {"url": "...CS100.html", "text": "Prerequisite: CS 100"},
        {"url": "...CS102.html", "text": "Next course: CS 102"}
    ]
}
```

**What Happens:**
1. ✓ Confirmed as course_page
2. → Added to results
3. → 2 links extracted and batch classified
4. ✓ Related courses discovered

### Example 3: Isolated Course Page

**Page Type:** Course page with no links to other courses

**URL:** `https://university.edu/courses/CS999.html`

**Content Analysis Result:**
```json
{
    "is_course_page": true,
    "confidence": 0.90,
    "course_code": "CS999",
    "has_other_course_links": false,
    "course_links_found": []
}
```

**What Happens:**
1. ✓ Confirmed as course_page
2. → Added to results
3. → No additional links to process
4. ✓ Single course captured

---

## Benefits

### 1. Higher Course Discovery Rate
- Finds courses through multiple paths
- Extracts embedded course links
- Follows breadcrumbs between related courses

### 2. Smarter Reclassification
- Doesn't discard valuable gateway pages
- Automatically adjusts classification based on content
- Ensures pages with course links are explored

### 3. Efficient API Usage
- Batch classifies extracted links
- Reuses existing classification infrastructure
- Caches results to avoid duplicate calls

### 4. Better Accuracy
- Two-stage verification reduces false positives
- Content analysis provides high confidence
- Extracted metadata improves data quality

---

## Testing

### Test Enhanced Verification

```bash
python tests/test_enhanced_verification.py
```

This test demonstrates:
- ✓ has_other_course_links detection
- ✓ Link extraction from verified pages
- ✓ Reclassification logic
- ✓ Batch classification workflow

### Test Content Verification

```bash
python tests/test_content_verification.py
```

### Run Full Scraping with Verification

```bash
python main.py --verify-content --depth 2
```

---

## Log Output Examples

### Successful Verification with Link Extraction

```
Verifying 5 course pages with content analysis
✓ Verified course page: https://example.edu/courses/CS101.html
  → Found 3 additional course links in verified page
Batch classifying 3 extracted course links
  → Added 2 newly discovered course pages
  → Added 1 course-relevant links
```

### Reclassification Example

```
↻ Reclassifying as course_relevant (has 5 course links): https://example.edu/~prof/teaching.html
Moving 1 pages from course_pages to course_relevant
Batch classifying 5 extracted course links
  → Added 4 newly discovered course pages
```

### Failed Verification

```
✗ Content verification failed (not a course page): https://example.edu/about.html (confidence: 0.15)
```

---

## Troubleshooting

### Issue: Too many reclassifications

**Cause:** Initial classification is too liberal with "course_page" label

**Solution:** 
- Adjust link classification prompt to be more conservative
- Increase confidence threshold in link classification
- Use heuristics to filter obvious non-course pages

### Issue: Missing course links in extraction

**Cause:** Links are dynamically loaded or in unusual format

**Solution:**
- AI can only extract links from static HTML
- Dynamic content (JavaScript) won't be captured
- Complex link structures may be missed

### Issue: Extracted links are low quality

**Cause:** AI extracting irrelevant links

**Solution:**
- Update content_analysis.txt prompt with better examples
- Adjust "Extracting Course Links" section
- Increase selectivity in link extraction instructions

---

## Architecture Diagram

```
┌──────────────────────────────────────────────────────────┐
│                  ENHANCED VERIFICATION                    │
└──────────────────────────────────────────────────────────┘
                          │
                          ▼
           ┌──────────────────────────────┐
           │   Initial Classification     │
           │   (Link Classifier)          │
           └──────────────────────────────┘
                          │
                          ▼
                  Classified as
                  "course_page"
                          │
                ┌─────────┴─────────┐
                │                   │
                ▼                   ▼
    ┌─────────────────┐    [No Verification]
    │  Verify Content │         │
    │  (if enabled)   │         └──→ Add to results
    └─────────────────┘
                │
                ▼
    ┌───────────────────────────┐
    │  AI Content Analysis      │
    │  - is_course_page?        │
    │  - has_other_course_links?│
    │  - course_links_found     │
    └───────────────────────────┘
                │
        ┌───────┴────────┐
        │                │
        ▼                ▼
  is_course=true   is_course=false
  confidence>0.5   has_links=true
        │                │
        ▼                ▼
   ✓ Verified      ↻ Reclassify
   Course Page     as course_relevant
        │                │
        └────────┬───────┘
                 │
                 ▼
        has_other_course_links?
                 │
            ┌────┴────┐
            │         │
           Yes        No
            │         │
            ▼         └──→ Done
   Extract & Batch
   Classify Links
            │
            ▼
   ┌─────────────────┐
   │ New Discoveries │
   │ - Course pages  │
   │ - Course relevant│
   └─────────────────┘
```

---

## Summary

The enhanced content verification system provides:

- ✅ **Intelligent gateway detection** via has_other_course_links
- ✅ **Automatic reclassification** of misclassified pages
- ✅ **Link extraction** from verified content
- ✅ **Batch classification** of extracted links
- ✅ **Higher discovery rate** of course pages
- ✅ **Better accuracy** through content analysis
- ✅ **Efficient API usage** via batching and caching

Enable with: `python main.py --verify-content`
