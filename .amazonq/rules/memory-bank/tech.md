# Technology Stack

## Programming Languages

- **Python 3.13** (required)
  - Modern Python features including type hints
  - `from __future__ import annotations` for forward references
  - Type annotations throughout codebase

## Core Dependencies

### Web Scraping
- **beautifulsoup4** (>=4.12.0, <5.0.0)
  - HTML parsing and link extraction
  - Used with lxml parser for performance
  
- **requests** (>=2.31.0, <3.0.0)
  - HTTP client for fetching web pages
  - Direct API calls to NVIDIA endpoints
  
- **lxml** (>=5.0.0, <6.0.0)
  - Fast XML/HTML parser backend for BeautifulSoup

### Configuration & Environment
- **python-dotenv** (>=1.0.0, <2.0.0)
  - Environment variable management
  - Loads .env file for API keys and settings

### AI Integration
- **NVIDIA API** (via requests)
  - No additional SDK required
  - Direct REST API calls using requests library
  - Models used:
    - `qwen/qwen3.5-397b-a17b` (link classification)
    - `meta/llama-3.1-70b-instruct` (content verification)
  - Free API keys from: https://build.nvidia.com/

## Development Tools

### Setup Scripts
- **setup.bat** - Windows CMD setup
- **setup.ps1** - Windows PowerShell setup
- **setup.sh** - Linux/Mac bash setup
- **clear_logs.bat** - Log cleanup utility

### Testing
- Test files in `tests/` directory
- Unit tests for configuration, content verification, filtering
- Example scripts for testing components

## Build & Dependency Management

### Installation
```bash
# Install dependencies
pip install -r requirements.txt

# Or using setup scripts
# Windows CMD:
setup.bat

# Windows PowerShell:
.\setup.ps1

# Linux/Mac:
chmod +x setup.sh
./setup.sh
```

### Environment Setup
```bash
# Copy template and configure
cp template.env .env

# Edit .env with your API keys
# Single key:
NVIDIA_API_KEY=nvapi-xxxxx

# Multiple keys (recommended):
NVIDIA_API_KEY_1=nvapi-xxxxx
NVIDIA_API_KEY_2=nvapi-yyyyy
NVIDIA_API_KEY_3=nvapi-zzzzz
```

## Development Commands

### Running the Application

**Stage 1: Link Extraction and Classification**
```bash
# Basic usage (default URL)
python main_scrape.py

# Custom URL
python main_scrape.py --url "https://example.edu/courses"

# Control depth
python main_scrape.py --depth 5

# Disable AI classification
python main_scrape.py --no-ai

# Custom output
python main_scrape.py --output "data/my_links.json"

# Combined options
python main_scrape.py --url "https://university.edu" --depth 3 --output "data/results.json"
```

**Stage 2: Course Content Analysis**
```bash
# Process URLs from Stage 1
python main_data.py

# Reads from: data/unique_course_urls.csv
# Outputs to: data/courses_output.csv
```

### Configuration

**Centralized in setup/config.py:**
- `SCRAPER_TIMEOUT = 45` - Request timeout (seconds)
- `SCRAPER_DELAY = 1` - Delay between requests (seconds)
- `MAX_SCRAPING_DEPTH = 7` - Maximum recursion depth
- `BATCH_SIZE = 7` - Links per API batch
- `BATCH_API_TIMEOUT = 120` - Batch API timeout (seconds)
- `BATCH_INTER_DELAY = 2` - Delay between batches (seconds)
- `BATCH_MAX_RETRIES = 3` - Retry attempts for failed batches
- `MAX_CONTENT_LENGTH = 8000` - Max characters for content analysis

**AI Model Configuration:**
```python
# Link Classification (Stage 1)
LINK_CLASSIFICATION_MODEL = "qwen/qwen3.5-397b-a17b"
LINK_CLASSIFICATION_TEMPERATURE = 0.2
LINK_CLASSIFICATION_MAX_TOKENS = 512
LINK_CLASSIFICATION_TOP_P = 0.9

# Content Verification (Stage 2)
CONTENT_VERIFICATION_MODEL = "meta/llama-3.1-70b-instruct"
CONTENT_VERIFICATION_TEMPERATURE = 0.1
CONTENT_VERIFICATION_MAX_TOKENS = 1024
CONTENT_VERIFICATION_TOP_P = 0.95
```

### Logging

**Log Files:**
- `logs/main.log` - Stage 1 scraping logs
- `logs/main_data.log` - Stage 2 analysis logs
- `logs/scraper.log` - Detailed scraper activity

**Log Level:**
- Default: INFO
- Configurable via LOG_LEVEL environment variable
- Format: `%(asctime)s - %(name)s - %(levelname)s - %(message)s`

**Clear Logs:**
```bash
# Windows
setup\clear_logs.bat

# Manual
rm logs/*.log
```

### Testing

```bash
# Run specific tests
python tests/test_config.py
python tests/test_content_verification.py
python tests/test_enhanced_verification.py

# Run examples
python tests/examples.py
```

## Data Formats

### Input
- **CSV**: URLs for Stage 2 processing
- **Environment variables**: API keys and configuration

### Output
- **JSON**: Classified links with metadata (Stage 1)
- **CSV**: Structured course database (Stage 2)
- **JSON**: Classification cache for performance

### Cache
- `data/link_classification_cache.json` - Persistent classification cache
- Key: URL, Value: classification result with confidence and reasoning

## API Integration

### NVIDIA API
- **Endpoint**: https://integrate.api.nvidia.com/v1/chat/completions
- **Authentication**: Bearer token (API key)
- **Request Format**: OpenAI-compatible chat completions
- **Response Format**: JSON with choices array

### Rate Limiting Strategy
- Multiple API keys with round-robin rotation
- Configurable delays between requests
- Automatic retry with exponential backoff
- Per-key usage tracking

### API Key Management
```python
from utils.api_key_manager import get_key_manager

manager = get_key_manager()
api_key = manager.get_next_key()  # Automatic rotation
manager.report_success(api_key)
manager.print_stats()  # Usage statistics
```

## Performance Considerations

- **Batch Processing**: Process multiple links per API call (BATCH_SIZE=7)
- **Caching**: Avoid redundant classifications
- **Concurrent Keys**: Multiple API keys increase throughput
- **Rate Limiting**: Polite delays prevent server overload
- **Timeout Handling**: Configurable timeouts with retry logic

## Security

- **API Keys**: Stored in .env (gitignored)
- **No Hardcoded Secrets**: All sensitive data in environment
- **Template Provided**: template.env for easy setup
- **PII Handling**: No personal data stored or transmitted
