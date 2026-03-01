# Product Overview

## Project Purpose

An intelligent web scraping tool that extracts and analyzes academic course information from university websites. The system uses AI-powered classification to distinguish between course-relevant content, navigation links, and irrelevant pages, enabling efficient recursive scraping of educational content.

## Value Proposition

- **Intelligent Filtering**: Combines heuristic patterns with AI classification to identify course-relevant pages while filtering out navigation and unrelated content
- **Two-Stage Verification**: Stage 1 classifies links based on URL/context; Stage 2 verifies actual page content for course information
- **Scalable API Management**: Supports multiple NVIDIA API keys with automatic rotation to increase rate limits and throughput
- **Comprehensive Data Extraction**: Extracts structured course data including titles, codes, credits, instructors, and descriptions
- **Efficient Caching**: Caches classification results to avoid redundant API calls and reduce costs

## Key Features

### Link Classification (Stage 1)
- Extracts all links from web pages with proper URL resolution
- Uses AI (Qwen 3.5 397B) to classify links as back links, course-relevant, or irrelevant
- Batch processing of links for efficiency (configurable batch size)
- Smart heuristics for common navigation patterns
- Classification caching to minimize API usage

### Content Verification (Stage 2)
- Analyzes actual page HTML content to verify course pages
- Uses AI (Llama 3.1 70B) to extract structured course data
- Identifies conflicts between URL classification and content analysis
- Flags pages needing manual review
- Extracts: course title, code, credits, instructor, description, prerequisites

### Recursive Scraping
- Follows course-relevant links up to configurable depth (default: 7 levels)
- Same-domain filtering to stay within target website
- Configurable delays to respect server resources
- Comprehensive logging for monitoring and debugging

### API Key Management
- Multiple NVIDIA API key support with round-robin rotation
- Automatic failover if a key encounters errors
- Per-key usage statistics and error tracking
- Increases effective rate limits proportionally to number of keys

### Data Export
- Structured JSON output for scraped links with classifications
- CSV database for course information with verification flags
- Detailed statistics on scraping results
- Conflict and recheck flags for quality control

## Target Users

- **Academic Researchers**: Collecting course data for curriculum analysis
- **Education Data Scientists**: Building datasets of university course offerings
- **University Administrators**: Analyzing course structures across institutions
- **Students**: Discovering courses and academic programs

## Use Cases

1. **Course Catalog Scraping**: Extract all courses from a university department website
2. **Curriculum Analysis**: Compare course offerings across multiple institutions
3. **Academic Program Discovery**: Find specialized courses and programs
4. **Course Information Extraction**: Build structured databases from unstructured web content
5. **Educational Content Mining**: Collect syllabi, course descriptions, and prerequisites

## Output Format

### Stage 1: Link Classification (JSON)
```json
{
  "base_url": "https://university.edu",
  "visited_urls": ["url1", "url2"],
  "course_relevant_links": [
    {
      "url": "https://university.edu/course",
      "text": "Course Title",
      "is_course_relevant": true,
      "confidence": 0.95,
      "reasoning": "Link points to course syllabus"
    }
  ],
  "stats": {
    "total_visited": 10,
    "course_relevant": 5,
    "back_links": 2,
    "irrelevant": 3
  }
}
```

### Stage 2: Course Data (CSV)
- url, course_title, course_code, credits, instructor, description
- is_course_page, confidence, reasoning
- recheck_needed, conflict_flag (quality control)
