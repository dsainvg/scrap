# Content Verification Feature

## Overview

The content verification feature adds a **second layer of validation** for course pages by analyzing their actual content. This helps ensure higher accuracy in identifying genuine course pages and can extract additional course links found within the content.

## How It Works

### Two-Stage Process

1. **Stage 1: Link Classification** (First AI Model)
   - Analyzes URLs and surrounding HTML context
   - Classifies links as: course pages, course-relevant, back links, or irrelevant
   - Uses model: `qwen/qwen3.5-397b-a17b`

2. **Stage 2: Content Verification** (Second AI Model) ✨ NEW
   - Fetches and analyzes the actual page content
   - Verifies if it's truly a course page
   - Extracts course metadata (code, name, semester)
   - Finds additional course links within the content
   - Uses model: `meta/llama-3.1-70b-instruct`

## Usage

### Command Line

Enable content verification with the `--verify-content` flag:

```bash
# Basic usage with content verification
python main.py --verify-content

# With custom settings
python main.py --verify-content --depth 3 --save-interval 100

# Full example
python main.py --url "https://cse.iitkgp.ac.in/faculty4.php" \
               --depth 2 \
               --verify-content \
               --save-interval 50
```

### Programmatic Usage

```python
from utils.scraper import IntelligentScraper

# Initialize with content verification
scraper = IntelligentScraper(
    base_url="https://example.edu/",
    use_ai_classification=True,
    verify_course_content=True,  # Enable verification
    save_interval=200
)

# Run scraping
results = scraper.scrape(max_depth=2)
```

### Direct Content Analysis

You can also use the content verification function independently:

```python
from utils.link_classifier import LinkClassifier

classifier = LinkClassifier()

# Verify a single URL
result = classifier.verify_course_page_content(
    url="https://example.edu/courses/CS101/"
)

if result:
    print(f"Is course page: {result['is_course_page']}")
    print(f"Confidence: {result['confidence']}")
    print(f"Course code: {result['course_code']}")
    print(f"Course name: {result['course_name']}")
    print(f"Semester: {result['semester']}")
    
    # Check for extracted course links
    for link in result['course_links_found']:
        print(f"Found: {link['url']}")
```

## What It Verifies

The content analyzer checks for:

- ✅ Course code/number (e.g., CS101, MATH-202)
- ✅ Course title and name
- ✅ Syllabus or course outline
- ✅ Lecture schedule with topics/dates
- ✅ Assignments, homework, projects
- ✅ Course materials, slides, notes
- ✅ Grading policy
- ✅ Office hours
- ✅ Prerequisites
- ✅ Semester/year information
- ✅ Instructor information

## Output Format

### Verification Result

```json
{
    "is_course_page": true,
    "confidence": 0.95,
    "course_code": "CS60050",
    "course_name": "Introduction to Algorithms",
    "semester": "Autumn 2024",
    "reasoning": "Page contains course code, syllabus, assignments",
    "course_links_found": [
        {
            "url": "https://example.edu/courses/CS101/",
            "text": "CS 101: Data Structures",
            "likely_course_code": "CS101"
        }
    ]
}
```

### Enhanced Course Page Data

When content verification is enabled, course pages in the output include:

```json
{
    "url": "https://example.edu/course/CS101/",
    "text": "CS 101",
    "classification": "course_page",
    "content_verified": true,
    "verification_confidence": 0.95,
    "verified_course_code": "CS101",
    "verified_course_name": "Introduction to Programming",
    "verified_semester": "Fall 2024"
}
```

## Benefits

1. **Higher Accuracy**: Double-checks that classified course pages are genuine
2. **Metadata Extraction**: Automatically extracts course codes, names, and semesters
3. **Link Discovery**: Finds additional course links embedded in content
4. **Quality Control**: Filters out false positives from initial classification

## Cost Considerations

⚠️ **Important**: Content verification makes additional API calls (one per course page)

- **Without verification**: ~1 API call per 10 links
- **With verification**: +1 API call per verified course page

**Recommendation**: Enable for final/production scraping when accuracy is critical

## Configuration

### Model Selection

Default models:
- **Link Classification**: `qwen/qwen3.5-397b-a17b` (detailed analysis)
- **Content Verification**: `meta/llama-3.1-70b-instruct` (fast content parsing)

Change the content model:

```python
result = classifier.verify_course_page_content(
    url="https://example.edu/course/",
    content_model="qwen/qwen3.5-397b-a17b"  # Use a different model
)
```

### Rate Limiting

Content verification includes automatic rate limiting:
- 0.5 second delay between verification requests
- Prevents API rate limit issues

## Testing

Run the test script to see it in action:

```bash
python tests/test_content_verification.py
```

This will:
1. Test content verification on sample URLs
2. Show extracted course information
3. Display found course links

## Prompts

Content verification uses a specialized prompt:
- **Location**: `prompts/content_analysis.txt`
- **Purpose**: Instructs AI to analyze page content and extract course information
- **Customizable**: Edit the prompt to adjust verification criteria

## Example Output

```
Verifying course page content: https://cse.iitkgp.ac.in/~pawang/courses/ALGO21.html
Extracted 6543 characters from https://cse.iitkgp.ac.in/~pawang/courses/ALGO21.html

✓ Verification Complete:
  Is Course Page: True
  Confidence: 0.95
  Course Code: CS41003
  Course Name: Algorithms-I
  Semester: Autumn 2021
  Reasoning: Contains course code, schedule, assignments, and grading policy
  
  Found 3 course links:
    1. /~pawang/courses/ALGO20.html
       Text: Previous offering (2020)
       Code: CS41003
    2. /~pawang/courses/DS21.html
       Text: Data Structures
       Code: CS21003
    3. /~pawang/courses/FLAT19.html
       Text: Formal Languages
       Code: CS21004
```

## When to Use

### ✅ Use Content Verification When:
- Accuracy is critical
- You need course metadata (codes, names, semesters)
- False positives are a concern
- Budget allows for additional API calls
- Final production scraping

### ❌ Skip Content Verification When:
- Initial exploration/testing
- Working with limited API credits
- Speed is more important than accuracy
- Link classification alone is sufficient

## Troubleshooting

**Issue**: Content verification is slow
- **Solution**: It's normal; each page needs to be fetched and analyzed

**Issue**: Some pages fail verification
- **Solution**: Pages may be inaccessible or have unusual formats; they're marked as `content_verified: false`

**Issue**: No course links extracted
- **Solution**: Page may not contain links to other courses; this is normal

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
