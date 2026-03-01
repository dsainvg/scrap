# Project Structure

## Directory Organization

```
SCRAPING/
├── main_scrape.py          # Stage 1: Link extraction and classification
├── main_data.py            # Stage 2: Course content analysis and verification
├── requirements.txt        # Python dependencies
├── template.env            # Environment variables template
├── .env                    # Actual environment variables (gitignored)
├── README.md              # Comprehensive project documentation
│
├── utils/                  # Core reusable modules
│   ├── __init__.py
│   ├── scraper.py         # Intelligent recursive web scraper
│   ├── link_classifier.py # AI-powered link classification agent
│   ├── link_extractor.py  # HTML link extraction utilities
│   ├── course_analyzer.py # Course page content analysis
│   └── api_key_manager.py # Multiple API key rotation manager
│
├── setup/                  # Configuration and setup scripts
│   ├── config.py          # Centralized configuration settings
│   ├── setup.bat          # Windows CMD setup script
│   ├── setup.ps1          # Windows PowerShell setup script
│   ├── setup.sh           # Linux/Mac setup script
│   └── clear_logs.bat     # Log cleanup utility
│
├── prompts/               # AI system prompts
│   ├── sys.txt            # Stage 1: Link classification prompt
│   ├── course_page_analysis.txt  # Stage 2: Course content analysis prompt
│   └── content_analysis.txt      # Alternative content analysis prompt
│
├── data/                  # Output data and caches
│   ├── scraped_links.json           # Stage 1 output: classified links
│   ├── unique_course_urls.csv       # Filtered course URLs for Stage 2
│   ├── courses_output.csv           # Stage 2 output: course database
│   ├── link_classification_cache.json  # Classification cache
│   └── old_data/          # Archived previous runs
│
├── logs/                  # Application logs
│   ├── main.log           # Stage 1 scraping logs
│   ├── main_data.log      # Stage 2 analysis logs
│   └── scraper.log        # Detailed scraper activity
│
├── docs/                  # Additional documentation
│   ├── QUICKSTART.md
│   ├── CONFIG_QUICK_REF.md
│   ├── MODEL_CONFIGURATION.md
│   ├── CONTENT_VERIFICATION.md
│   └── ENHANCED_VERIFICATION.md
│
└── tests/                 # Test suite
    ├── test_config.py
    ├── test_content_verification.py
    ├── test_enhanced_verification.py
    ├── test_file_filtering.py
    ├── test_html_context.py
    ├── test_stage2_courses_page.py
    └── examples.py
```

## Core Components

### Entry Points

**main_scrape.py** (Stage 1)
- Entry point for link extraction and classification pipeline
- Initializes IntelligentScraper with base URL
- Outputs: scraped_links.json, unique_course_urls.csv
- Logs to: logs/main.log

**main_data.py** (Stage 2)
- Entry point for course content analysis pipeline
- Processes URLs from unique_course_urls.csv
- Outputs: courses_output.csv with structured course data
- Logs to: logs/main_data.log

### Reusable Utilities (utils/)

**scraper.py** - IntelligentScraper class
- Recursive web scraping with depth control
- Same-domain filtering
- Link extraction and deduplication
- Integration with LinkClassifier for AI-powered filtering
- Rate limiting and polite crawling

**link_classifier.py** - LinkClassifier class
- AI-powered link classification using NVIDIA API
- Batch processing for efficiency
- Classification caching to reduce API calls
- Heuristic pre-filtering for common patterns
- Confidence scoring and reasoning

**course_analyzer.py** - Course content analysis
- Fetches and analyzes HTML content of course pages
- AI-powered extraction of structured course data
- Conflict detection between URL classification and content
- CSV output generation with quality flags
- Reusable functions: process_url(), write_csv(), load_data()

**link_extractor.py** - HTML parsing utilities
- BeautifulSoup-based link extraction
- URL normalization and resolution
- Link text and title extraction
- Domain filtering helpers

**api_key_manager.py** - APIKeyManager class (Singleton)
- Multiple API key loading from environment
- Round-robin key rotation
- Per-key usage and error tracking
- Thread-safe operations
- Statistics reporting

### Configuration (setup/)

**config.py** - Centralized settings
- Scraper configuration (timeout, delay, depth)
- AI model settings for both stages
- Batch processing parameters
- API endpoints and cache paths
- Content analysis limits
- Validation of all settings

### AI Prompts (prompts/)

**sys.txt** - Stage 1 link classification
- Defines back link patterns
- Defines course-relevant link criteria
- Classification guidelines and rules

**course_page_analysis.txt** - Stage 2 content verification
- Structured data extraction instructions
- Course information field definitions
- Conflict detection rules
- Quality control guidelines

## Architectural Patterns

### Two-Stage Pipeline Architecture

**Stage 1: Link Discovery**
1. Scraper extracts all links from pages
2. LinkClassifier filters and classifies links
3. Recursive scraping follows course-relevant links
4. Output: classified link database

**Stage 2: Content Verification**
1. Load course URLs from Stage 1
2. Fetch actual page content
3. AI analyzes content for course information
4. Extract structured data with quality flags
5. Output: course database with verification

### Separation of Concerns

- **Entry points** (main_*.py): Minimal orchestration logic
- **Utils modules**: Reusable, testable components
- **Configuration**: Centralized in setup/config.py
- **Prompts**: Externalized AI instructions
- **Data**: Separate directory for outputs and caches

### Caching Strategy

- Classification results cached by URL
- Avoids redundant API calls across runs
- JSON-based persistent cache
- Automatic cache loading/saving

### Error Handling

- Comprehensive logging at all levels
- Graceful degradation on API failures
- Failed URL tracking and reporting
- Retry logic with exponential backoff
- Quality flags for manual review

### Extensibility

- Modular design allows component reuse
- Configuration-driven behavior
- Pluggable AI models via config
- Easy to add new classification rules
- Testable components with clear interfaces
