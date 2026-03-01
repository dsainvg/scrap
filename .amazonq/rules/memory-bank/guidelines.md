# Development Guidelines

## Code Quality Standards

### Documentation Style
- **Module docstrings**: Every module starts with a triple-quoted docstring explaining purpose, public API, and usage examples
- **Function docstrings**: Use structured format with Parameters, Returns, and Raises sections
- **Inline comments**: Explain "why" not "what" - code should be self-documenting
- **Section separators**: Use comment blocks with `=` or `-` characters to visually separate logical sections

Example from course_analyzer.py:
```python
"""
utils/course_analyzer.py
------------------------
Reusable pipeline for IIT Kharagpur course page analysis.

Public API
----------
fetch_html(url, timeout, max_retries) -> str | None
process_url(url) -> dict | None
"""
```

### Type Annotations
- **Modern Python typing**: Use `from __future__ import annotations` for forward references
- **Type hints everywhere**: All function parameters and return types are annotated
- **Optional types**: Use `Optional[Type]` for nullable values
- **Collection types**: Use `List[Dict]`, `Set[str]`, `Dict[str, Any]` for clarity
- **Union types**: Prefer `Optional[X]` over `Union[X, None]`

Example:
```python
def fetch_html(
    url: str,
    timeout: int = SCRAPER_TIMEOUT,
    max_retries: int = 2,
) -> Optional[str]:
```

### Naming Conventions
- **Functions/methods**: `snake_case` - descriptive verb phrases (e.g., `extract_manual_fields`, `classify_link`)
- **Classes**: `PascalCase` - nouns (e.g., `LinkClassifier`, `IntelligentScraper`, `APIKeyManager`)
- **Constants**: `UPPER_SNAKE_CASE` - module-level or config values (e.g., `MAX_SCRAPING_DEPTH`, `BATCH_SIZE`)
- **Private helpers**: Prefix with `_` (e.g., `_load_cache`, `_parse_ai_json`, `_normalize_url`)
- **Internal constants**: Prefix with `_` for module-private (e.g., `_FILE_EXTS`, `_MANUAL_TO_AI`)

### Code Organization
- **Imports grouped**: Standard library, third-party, local imports separated by blank lines
- **Path manipulation first**: Set up `sys.path` before importing local modules
- **Environment loading early**: Call `load_dotenv()` near the top of entry points
- **Logging setup**: Configure logging before importing modules that use it
- **Constants after imports**: Define module constants after all imports

### Error Handling
- **Specific exceptions**: Catch specific exception types, not bare `except:`
- **Logging errors**: Always log errors with context using `logger.error()`
- **Graceful degradation**: Return fallback values or None rather than crashing
- **Retry logic**: Implement exponential backoff for transient failures (network, API)
- **User-friendly messages**: Log actionable error messages with suggestions

Example from link_classifier.py:
```python
except requests.exceptions.RequestException as e:
    logger.error(f"API request error for {url}: {str(e)}")
    if self.use_key_rotation and self.key_manager and api_key:
        self.key_manager.report_error(api_key)
    return {
        'url': url,
        'is_back_link': False,
        'is_course_relevant': False,
        'confidence': 0.0,
        'reasoning': f'API request error: {str(e)}',
        'error': True
    }
```

## Architectural Patterns

### Singleton Pattern
- **API Key Manager**: Uses thread-safe singleton with double-checked locking
- **Global instance**: Module-level `_key_manager_instance` with `_instance_lock`
- **Factory function**: `get_key_manager()` provides access to singleton
- **Reset capability**: `reset_key_manager()` for testing

Example from api_key_manager.py:
```python
_key_manager_instance: Optional[APIKeyManager] = None
_instance_lock = threading.Lock()

def get_key_manager() -> APIKeyManager:
    global _key_manager_instance
    if _key_manager_instance is None:
        with _instance_lock:
            if _key_manager_instance is None:
                _key_manager_instance = APIKeyManager()
    return _key_manager_instance
```

### Separation of Concerns
- **Entry points minimal**: main_*.py files orchestrate, don't implement logic
- **Utils are reusable**: All core logic in utils/ modules, importable anywhere
- **Configuration centralized**: All settings in setup/config.py with validation
- **Prompts externalized**: AI instructions in prompts/ directory, loaded at runtime

### Caching Strategy
- **Persistent cache**: JSON file-based cache for API results
- **Cache on read**: Check cache before making API calls
- **Cache on write**: Save to file immediately after successful API call
- **Normalized keys**: Use URL normalization for consistent cache keys
- **Statistics tracking**: Track cache hits/misses for performance monitoring

Example from link_classifier.py:
```python
def _get_from_cache(self, url: str) -> Optional[Dict]:
    cache_key = self._get_cache_key(url)
    if cache_key in self.classification_cache:
        self.cache_hits += 1
        logger.info(f"[OK] Cache HIT for: {url}")
        return self.classification_cache[cache_key]
    else:
        self.cache_misses += 1
        return None

def _store_in_cache(self, url: str, result: Dict):
    cache_key = self._get_cache_key(url)
    self.classification_cache[cache_key] = result
    self._save_cache()  # Persist immediately
```

### Batch Processing Pattern
- **Batch API calls**: Process multiple items per API request to reduce latency
- **Cache-first approach**: Check cache for ALL items before batching
- **Configurable batch size**: Use `BATCH_SIZE` from config for tuning
- **Retry with backoff**: Exponential backoff for timeout errors
- **Inter-batch delays**: `BATCH_INTER_DELAY` to avoid rate limiting

Example from link_classifier.py:
```python
def classify_links_batch(self, links: List[Dict], context_url: str = None, batch_size: int = 10):
    # STEP 1: Check cache for ALL links BEFORE batch processing
    uncached_links = []
    for link_info in links:
        cached_result = self._get_from_cache(link_info['url'])
        if not cached_result:
            uncached_links.append(link_info)
    
    # STEP 2: Process only uncached links in batches
    for i in range(0, len(uncached_links), batch_size):
        batch = uncached_links[i:i+batch_size]
        # ... API call with retry logic ...
        
        # STEP 3: Store each result in cache immediately
        for link_info, result in zip(batch, batch_results):
            self._store_in_cache(link_info['url'], result)
```

### Deduplication Strategy
- **URL normalization**: Lowercase scheme/host, strip trailing slash, remove fragment
- **Global seen sets**: Module-level sets track URLs across all categories
- **Normalize before check**: Always normalize URLs before deduplication checks
- **Final dedup pass**: Safety net deduplication before saving results

Example from scraper.py:
```python
@staticmethod
def _normalize_url(url: str) -> str:
    try:
        from urllib.parse import urlparse, urlunparse
        p = urlparse(url.strip())
        path = p.path.rstrip('/') or '/'
        return urlunparse((
            p.scheme.lower(),
            p.netloc.lower(),
            path,
            p.params,
            p.query,
            ''  # drop fragment
        ))
    except Exception:
        return url.strip().lower()

# Usage with global seen sets
_norm = self._normalize_url(link['url'])
if _norm not in self._seen_course_pages:
    self._seen_course_pages.add(_norm)
    self.course_pages.append(link)
```

## Common Implementation Patterns

### Configuration Import Pattern
- **Add setup to path**: Use `sys.path.insert(0, ...)` to make setup/ importable
- **Import from setup.config**: All modules import settings from centralized config
- **No hardcoded values**: All magic numbers come from config constants

Example:
```python
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'setup'))
from setup.config import (
    LINK_CLASSIFICATION_MODEL,
    BATCH_SIZE,
    NVIDIA_API_ENDPOINT,
)
```

### Logging Pattern
- **Module-level logger**: `logger = logging.getLogger(__name__)`
- **Structured messages**: Use f-strings with context (URL, counts, status)
- **Log levels**: INFO for progress, WARNING for issues, ERROR for failures
- **Visual separators**: Use `=` lines for major sections in logs
- **Detailed classification logs**: Log AI decisions with reasoning

Example:
```python
logger.info(f"\n{'='*80}")
logger.info(f"AI CLASSIFICATION RESULT")
logger.info(f"URL: {url}")
logger.info(f"Is Course Relevant: {result['is_course_relevant']}")
logger.info(f"Confidence: {result.get('confidence', 0.0):.2f}")
logger.info(f"Reasoning: {result.get('reasoning', 'N/A')}")
logger.info(f"{'='*80}\n")
```

### API Call Pattern with Key Rotation
- **Get key from manager**: `api_key = self.key_manager.get_next_key()`
- **Report success/error**: Always report outcome to key manager
- **Timeout handling**: Use configurable timeouts from config
- **Error propagation**: Log errors but return fallback values

Example:
```python
api_key = self.key_manager.get_next_key()
try:
    response = requests.post(
        self.invoke_url,
        headers={"Authorization": f"Bearer {api_key}"},
        json=payload,
        timeout=30
    )
    response.raise_for_status()
    self.key_manager.report_success(api_key)
    return response.json()
except requests.exceptions.RequestException as e:
    self.key_manager.report_error(api_key)
    logger.error(f"API request failed: {str(e)}")
    return fallback_value
```

### HTML Parsing Pattern
- **BeautifulSoup with lxml**: Use `BeautifulSoup(html, 'html.parser')` or `'lxml'`
- **Remove noise**: Strip script, style, nav, footer, header tags
- **Extract text cleanly**: Use `get_text()` with separator and strip
- **Truncate content**: Limit to `MAX_CONTENT_LENGTH` for API calls
- **URL resolution**: Use `urljoin(base_url, href)` for relative URLs

Example:
```python
soup = BeautifulSoup(html_content, 'html.parser')
for script in soup(["script", "style", "nav", "footer", "header"]):
    script.decompose()
text = soup.get_text()
lines = (line.strip() for line in text.splitlines())
chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
text = ' '.join(chunk for chunk in chunks if chunk)
if len(text) > MAX_CONTENT_LENGTH:
    text = text[:MAX_CONTENT_LENGTH] + "..."
```

### Prompt Template Pattern
- **External prompt files**: Store prompts in prompts/ directory as .txt files
- **Load at runtime**: Read prompt file in `__init__` or lazy load
- **Fallback prompts**: Provide inline default if file not found
- **Simple substitution**: Use `.replace()` for placeholders, not f-strings
- **JSON in prompts**: Avoid escaping issues by using plain string replacement

Example from course_analyzer.py:
```python
def _load_prompt_template() -> str:
    try:
        with open(_PROMPT_FILE, "r", encoding="utf-8") as fh:
            return fh.read()
    except FileNotFoundError:
        logger.warning(f"Prompt file not found. Using inline fallback.")
        return "Default prompt text..."

def _render_prompt(template: str, manual_json: str, html_snippet: str) -> str:
    return (
        template
        .replace("{manual_json}", manual_json)
        .replace("{html_snippet}", html_snippet)
    )
```

### Recursive Scraping Pattern
- **Depth tracking**: Pass `current_depth` parameter through recursion
- **Visited set**: Maintain `visited_urls` set to avoid cycles
- **Selective recursion**: Only recurse into course-relevant links, not course pages
- **Rate limiting**: Sleep between requests using `SCRAPER_DELAY`
- **Periodic saves**: Save progress every N links to prevent data loss

Example from scraper.py:
```python
def scrape_page(self, url: str, max_depth: int = 2, current_depth: int = 0):
    if url in self.visited_urls:
        return
    if current_depth > max_depth:
        return
    
    self.visited_urls.add(url)
    extracted_links = self.extract_all_links(url)
    classified = self.classifier.filter_links(extracted_links, context_url=url)
    
    # Only recurse into course-relevant links (catalogs, listings)
    if current_depth < max_depth:
        for link_info in classified['course_relevant']:
            if link_info['url'] not in self.visited_urls:
                time.sleep(SCRAPER_DELAY)
                self.scrape_page(link_info['url'], max_depth, current_depth + 1)
```

### Thread Safety Pattern
- **Use locks**: `threading.Lock()` for shared state
- **Context managers**: Always use `with self.lock:` for critical sections
- **Atomic operations**: Keep locked sections minimal
- **Deque for rotation**: Use `collections.deque` for efficient round-robin

Example from api_key_manager.py:
```python
def __init__(self):
    self.key_queue = deque(self.api_keys)
    self.lock = threading.Lock()
    self.usage_stats = {key: 0 for key in self.api_keys}

def get_next_key(self) -> str:
    with self.lock:
        self.key_queue.rotate(-1)
        key = self.key_queue[0]
        self.usage_stats[key] += 1
        return key
```

## Testing and Validation

### Configuration Validation
- **Validate on load**: Check all config values in setup/config.py
- **Raise ValueError**: Fail fast with clear error messages
- **Range checks**: Validate numeric ranges (timeouts, temperatures, etc.)
- **Type checks**: Ensure correct types for all settings

Example from setup/config.py:
```python
if SCRAPER_TIMEOUT < 1:
    raise ValueError("SCRAPER_TIMEOUT must be at least 1 second")
if BATCH_SIZE < 1:
    raise ValueError("BATCH_SIZE must be at least 1")
if LINK_CLASSIFICATION_TEMPERATURE < 0 or LINK_CLASSIFICATION_TEMPERATURE > 2:
    raise ValueError("LINK_CLASSIFICATION_TEMPERATURE must be between 0 and 2")
```

### Input Validation
- **Check for None**: Validate required parameters are not None
- **Empty checks**: Handle empty strings, lists, dicts gracefully
- **URL validation**: Use `urlparse()` to validate URL structure
- **Encoding handling**: Always specify `encoding='utf-8'` for file operations

## Performance Optimization

### Minimize API Calls
- **Cache aggressively**: Check cache before every API call
- **Batch processing**: Group multiple items per API request
- **Heuristic filtering**: Use regex patterns to filter obvious cases
- **Early returns**: Skip processing when possible

### Efficient Data Structures
- **Sets for membership**: Use sets for O(1) lookup (visited URLs, seen items)
- **Deque for rotation**: Use `collections.deque` for efficient rotation
- **Generators**: Use generator expressions for memory efficiency
- **Counter for frequency**: Use `collections.Counter` for counting patterns

### Connection Pooling
- **Session reuse**: Use `requests.Session()` for connection pooling
- **Persistent headers**: Set headers once on session object
- **Timeout configuration**: Always specify timeouts to prevent hangs

Example from scraper.py:
```python
self.session = requests.Session()
self.session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
})
response = self.session.get(url, timeout=SCRAPER_TIMEOUT)
```

## Code Style Preferences

### String Formatting
- **f-strings preferred**: Use f-strings for readability and performance
- **Multi-line strings**: Use triple quotes for long strings
- **Path joining**: Use `os.path.join()` for cross-platform paths

### Boolean Logic
- **Explicit comparisons**: Use `if value is None:` not `if not value:`
- **Truthiness**: Use `if items:` for non-empty checks
- **Boolean returns**: Return boolean expressions directly

### Function Design
- **Single responsibility**: Each function does one thing well
- **Small functions**: Keep functions under 50 lines when possible
- **Pure functions**: Prefer functions without side effects
- **Default arguments**: Use defaults from config constants

### Class Design
- **Initialization**: Set up all state in `__init__`
- **Private methods**: Prefix helpers with `_`
- **Properties**: Use `@property` for computed attributes
- **Context managers**: Implement `__enter__`/`__exit__` when managing resources
