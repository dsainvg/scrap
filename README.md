# Intelligent Web Scraper with AI Link Classification

An intelligent web scraping tool that extracts links from web pages and uses AI to classify them as back links, course-relevant links, or irrelevant links. Perfect for scraping academic course information while filtering out navigation and unrelated content.

## Features

- **Intelligent Link Extraction**: Extracts all links from web pages with proper URL resolution
- **AI-Powered Classification**: Uses NVIDIA AI models (Qwen 3.5) to classify links as:
  - Back links (navigation, home, parent pages)
  - Course-relevant links (syllabi, curriculum, academic programs)
  - Irrelevant links (filtered out from further scraping)
- **Multiple API Key Rotation**: Support for multiple NVIDIA API keys with automatic rotation for higher rate limits
- **Smart Filtering**: Combines heuristics and AI for efficient link classification
- **Recursive Scraping**: Automatically follows course-relevant links up to a specified depth
- **Rate Limiting**: Built-in delays to respect server resources
- **Comprehensive Logging**: Detailed logs for debugging and monitoring
- **Data Export**: Saves results in structured JSON format
- **Usage Statistics**: Track API key usage and performance metrics

## Project Structure

```
SCRAPING/
├── main.py                 # Main entry point
├── template.env            # Environment variables template
├── requirements.txt        # Python dependencies
├── setup.ps1              # Windows PowerShell setup
├── setup.bat              # Windows CMD setup
├── setup.sh               # Linux/Mac setup
├── data/                   # Scraped data output
├── logs/                   # Log files
├── prompts/
│   └── sys.txt            # AI system prompt
└── utils/
    ├── scraper.py         # Intelligent scraper implementation
    ├── link_classifier.py # AI link classification agent
    └── api_key_manager.py # Multiple API key rotation manager
```
    └── link_classifier.py # AI link classification agent
```

## Installation

1. **Clone or download the project**

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**:
   - Copy `template.env` to `.env`
   - Add your NVIDIA API key(s):
   ```
   NVIDIA_API_KEY=your_actual_api_key_here
   ```
   - **For higher rate limits**, add multiple keys:
   ```
   NVIDIA_API_KEY_1=your_first_key
   NVIDIA_API_KEY_2=your_second_key
   NVIDIA_API_KEY_3=your_third_key
   ```
   - Get your free API key from: https://build.nvidia.com/

## Usage

### Basic Usage

Scrape with default settings (starts from IIT Kharagpur CSE faculty page):
```bash
python main.py
```

### Custom URL

Scrape a specific URL:
```bash
python main.py --url "https://example.edu/courses"
```

### Control Scraping Depth

Set maximum recursion depth (default is 2):
```bash
python main.py --depth 3
```

### Disable AI Classification

Extract all links without AI filtering (faster, but no classification):
```bash
python main.py --no-ai
```

### Custom Output Location

Specify output file location:
```bash
python main.py --output "data/my_results.json"
```

### Combined Options

```bash
python main.py --url "https://university.edu/courses" --depth 3 --output "data/courses.json"
```

## Output Format

The scraper generates a JSON file with the following structure:

```json
{
  "base_url": "https://example.edu",
  "visited_urls": ["url1", "url2", ...],
  "course_relevant_links": [
    {
      "url": "https://example.edu/course",
      "text": "Course Title",
      "is_course_relevant": true,
      "confidence": 0.95,
      "reasoning": "Link points to course syllabus"
    }
  ],
  "back_links": [...],
  "irrelevant_links": [...],
  "stats": {
    "total_visited": 10,
    "course_relevant": 5,
    "back_links": 2,
    "irrelevant": 3
  }
}
```

## Configuration

### Environment Variables

Edit `.env` file (copy from `template.env`):

- `NVIDIA_API_KEY`: Your NVIDIA API key (required for AI classification)
- `NVIDIA_API_KEY_1`, `NVIDIA_API_KEY_2`, etc.: Multiple API keys for rotation (optional)
- `NVIDIA_API_KEYS`: Comma-separated API keys (alternative to numbered keys)
- `NVIDIA_MODEL`: Model to use (default: `qwen/qwen3.5-397b-a17b`)
- `SCRAPER_TIMEOUT`: Request timeout in seconds (default: 30)
- `SCRAPER_DELAY`: Delay between requests in seconds (default: 1)
- `MAX_SCRAPING_DEPTH`: Maximum recursion depth (default: 2)
- `LOG_LEVEL`: Logging level (default: INFO)

### System Prompt

Customize the AI classification behavior by editing `prompts/sys.txt`. The prompt defines:
- What constitutes a "back link"
- What constitutes a "course-relevant link"
- Classification guidelines and rules

### Multiple API Keys for Higher Rate Limits

The scraper supports multiple NVIDIA API keys to increase effective rate limits. Keys are rotated automatically using round-robin.

**Setup options:**

1. **Numbered keys** (recommended):
```env
NVIDIA_API_KEY_1=nvapi-xxxxx
NVIDIA_API_KEY_2=nvapi-yyyyy
NVIDIA_API_KEY_3=nvapi-zzzzz
```

2. **Comma-separated**:
```env
NVIDIA_API_KEYS=key1,key2,key3
```

3. **Single key** (fallback):
```env
NVIDIA_API_KEY=nvapi-xxxxx
```

**Benefits:**
- Distributes API requests across multiple keys
- Increases effective rate limits proportionally
- Automatic failover if a key encounters errors
- Usage statistics tracked per key

At the end of scraping, you'll see statistics like:
```
API KEY USAGE STATISTICS
========================
Total Keys: 3
Total Requests: 150
Key ...abc123: 50 requests, 0 errors
Key ...def456: 50 requests, 0 errors
Key ...ghi789: 50 requests, 0 errors
```

## How It Works

1. **Initialization**: The scraper starts with a base URL and initializes the AI classifier with API key rotation
2. **Link Extraction**: All links are extracted from the page using BeautifulSoup
3. **Domain Filtering**: Only same-domain links are considered for classification
4. **Quick Heuristics**: Common back link patterns are filtered using regex patterns
5. **AI Classification**: Remaining links are sent to NVIDIA API for intelligent classification
6. **Recursive Scraping**: Course-relevant links are followed up to the specified depth
7. **Results Export**: All data is saved to a JSON file with comprehensive statistics

## AI Classification

The AI agent analyzes each link based on:
- URL structure and patterns
- Link text and title attributes
- Context from the source page
- Semantic understanding of course-related content

Classification confidence scores help prioritize which links to follow.

## Best Practices

- Start with a low depth (1-2) to test on a new domain
- Monitor API costs when scraping large sites
- Use `--no-ai` flag for initial exploration
- Check logs for errors and classification decisions
- Adjust system prompt for domain-specific needs

## Logging

Logs are saved to:
- `logs/main.log`: Overall application logs
- `logs/scraper.log`: Detailed scraping activity
- Console: Real-time progress updates

## Troubleshooting

**API Key Error**:
- Ensure `.env` file exists and contains valid `NVIDIA_API_KEY`
- Check that you've copied from `template.env`
- Get your free API key from: https://build.nvidia.com/

**No Links Found**:
- Check if the website blocks scrapers (user agent)
- Verify the URL is accessible
- Look at logs for HTTP errors

**Slow Performance**:
- Use `--no-ai` for faster extraction without classification
- Reduce `--depth` parameter
- Adjust `SCRAPER_DELAY` in `.env`

## License

MIT License - Feel free to use and modify for your projects.

## Contributing

Contributions welcome! Please submit issues and pull requests for:
- Bug fixes
- Performance improvements
- New classification features
- Better heuristics

## Credits

Built with:
- BeautifulSoup4 for HTML parsing
- Requests for HTTP handling
- NVIDIA AI API (Qwen 3.5) for intelligent classification

# Multiple API Keys Guide

## Why Use Multiple API Keys?

NVIDIA's free API tier has rate limits per API key. By using multiple keys and rotating between them, you can:

1. **Increase throughput** - Make more requests per minute
2. **Avoid rate limiting** - Distribute load across multiple keys
3. **Improve reliability** - Automatic failover if one key has issues

## How It Works

The `APIKeyManager` class automatically:
- Loads all available keys from your `.env` file
- Rotates keys using round-robin (fair distribution)
- Tracks usage statistics per key
- Reports errors for problematic keys
- Can remove bad keys from rotation

## Setup Examples

### Option 1: Numbered Keys (Recommended)

In your `.env` file:
```env
NVIDIA_API_KEY_1=nvapi-abc123...
NVIDIA_API_KEY_2=nvapi-def456...
NVIDIA_API_KEY_3=nvapi-ghi789...
```

The system will find all keys from `_1` to `_N`.

### Option 2: Comma-Separated

```env
NVIDIA_API_KEYS=nvapi-key1,nvapi-key2,nvapi-key3
```

### Option 3: Single Key (Fallback)

```env
NVIDIA_API_KEY=nvapi-single-key
```

## Getting Multiple API Keys

1. Go to https://build.nvidia.com/
2. Sign in with your account
3. Navigate to a model (e.g., Qwen 3.5)
4. Click "Get API Key"
5. Generate multiple keys (you can create several per account)
6. Add each key to your `.env` file

**Pro Tip**: If you have multiple email accounts, you can create one NVIDIA account per email and get additional API keys.

## Usage Statistics

After scraping completes, you'll see stats like:

```
API KEY USAGE STATISTICS
========================
Total Keys: 3
Total Requests: 150
Total Errors: 2
Error Rate: 1.33%

Per-Key Statistics:
  Key ...abc123:
    Requests: 50
    Errors: 1
  Key ...def456:
    Requests: 51
    Errors: 0
  Key ...ghi789:
    Requests: 49
    Errors: 1
```

## Rate Limit Math

**Single key**: ~60 requests/minute (NVIDIA free tier estimate)
**3 keys**: ~180 requests/minute
**5 keys**: ~300 requests/minute

**Example**: Scraping 100 pages with 20 links each = 2000 API calls
- With 1 key: ~33 minutes
- With 3 keys: ~11 minutes
- With 5 keys: ~7 minutes

## Implementation Details

The `APIKeyManager` uses:
- Thread-safe operations with locks
- `collections.deque` for efficient rotation
- Singleton pattern for global access
- Per-key error tracking

## Code Example

```python
from utils.api_key_manager import get_key_manager

# Get the key manager instance
manager = get_key_manager()

# Get next key (automatic rotation)
api_key = manager.get_next_key()

# Report success/error
manager.report_success(api_key)
manager.report_error(api_key)

# Get statistics
stats = manager.get_stats()
print(f"Total keys: {stats['total_keys']}")
print(f"Total requests: {stats['total_requests']}")

# Print formatted stats
manager.print_stats()
```

## Best Practices

1. **Start with 2-3 keys** to test the system
2. **Monitor error rates** - high errors might indicate bad keys
3. **Rotate keys periodically** - refresh old keys if needed
4. **Don't share keys** - keep them in `.env` (gitignored)
5. **Check quotas** - NVIDIA may have daily/monthly limits

## Troubleshooting

**"No API keys found" error**:
- Check your `.env` file exists
- Verify keys are in correct format
- Ensure no extra spaces or quotes

**High error rate on specific key**:
- The key might be expired or invalid
- Check your NVIDIA dashboard
- Generate a new key to replace it

**Keys not rotating evenly**:
- This is normal - slight variations occur
- Over time, distribution evens out

## Security Notes

- **Never commit** your `.env` file to git
- **Never share** API keys publicly
- **Rotate keys** if accidentally exposed
- **Use different keys** for different projects (optional)

## Advanced: Dynamic Key Management

For production use, consider:
- Loading keys from a secure vault (AWS Secrets Manager, Azure Key Vault)
- Implementing adaptive rotation based on error rates
- Auto-removing keys that consistently fail
- Monitoring and alerting for key health

The current implementation focuses on simplicity and reliability for research/academic use.
