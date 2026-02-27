"""
Configuration settings for the scraper.
All configuration is centralized here. Other files should import from this module.
"""

# Scraper Configuration
# Request timeout in seconds
SCRAPER_TIMEOUT = 45

# Delay between requests in seconds (to be polite to servers)
SCRAPER_DELAY = 1

# Maximum depth for recursive scraping
MAX_SCRAPING_DEPTH = 7

# Request timeout constant (used in scraper.py)
REQUEST_TIMEOUT = SCRAPER_TIMEOUT

# AI Model Configuration
# =====================

# Link Classification Model (Stage 1)
# Used for analyzing URLs and context to classify links
LINK_CLASSIFICATION_MODEL = "qwen/qwen3.5-397b-a17b"
LINK_CLASSIFICATION_TEMPERATURE = 0.2
LINK_CLASSIFICATION_MAX_TOKENS = 512
LINK_CLASSIFICATION_TOP_P = 0.9

# Content Verification Model (Stage 2)
# Used for analyzing actual page content to verify course pages
CONTENT_VERIFICATION_MODEL = "meta/llama-3.1-70b-instruct"
CONTENT_VERIFICATION_TEMPERATURE = 0.1
CONTENT_VERIFICATION_MAX_TOKENS = 1024
CONTENT_VERIFICATION_TOP_P = 0.95

# Batch Processing
# Number of links to process per API request for link classification.
# Smaller = faster per-batch response, fewer timeout failures. Keep ≤ 5 for large models.
BATCH_SIZE = 7

# Timeout in seconds for a single batch API call.
BATCH_API_TIMEOUT = 120

# Delay in seconds between consecutive batch API calls (avoids rate-limiting).
BATCH_INTER_DELAY = 2

# Maximum number of retries for a timed-out batch, with exponential backoff.
BATCH_MAX_RETRIES = 3

# API Configuration
NVIDIA_API_ENDPOINT = "https://integrate.api.nvidia.com/v1/chat/completions"

# Cache Configuration
CLASSIFICATION_CACHE_FILE = "data/link_classification_cache.json"

# Content Analysis
# Maximum characters of page content to send to AI for analysis
MAX_CONTENT_LENGTH = 8000

# Validate settings
if SCRAPER_TIMEOUT < 1:
    raise ValueError("SCRAPER_TIMEOUT must be at least 1 second")
if SCRAPER_DELAY < 0:
    raise ValueError("SCRAPER_DELAY cannot be negative")
if MAX_SCRAPING_DEPTH < 1:
    raise ValueError("MAX_SCRAPING_DEPTH must be at least 1")
if BATCH_SIZE < 1:
    raise ValueError("BATCH_SIZE must be at least 1")
if BATCH_API_TIMEOUT < 10:
    raise ValueError("BATCH_API_TIMEOUT must be at least 10 seconds")
if BATCH_INTER_DELAY < 0:
    raise ValueError("BATCH_INTER_DELAY cannot be negative")
if BATCH_MAX_RETRIES < 0:
    raise ValueError("BATCH_MAX_RETRIES cannot be negative")
if LINK_CLASSIFICATION_TEMPERATURE < 0 or LINK_CLASSIFICATION_TEMPERATURE > 2:
    raise ValueError("LINK_CLASSIFICATION_TEMPERATURE must be between 0 and 2")
if LINK_CLASSIFICATION_MAX_TOKENS < 64:
    raise ValueError("LINK_CLASSIFICATION_MAX_TOKENS must be at least 64")
if CONTENT_VERIFICATION_TEMPERATURE < 0 or CONTENT_VERIFICATION_TEMPERATURE > 2:
    raise ValueError("CONTENT_VERIFICATION_TEMPERATURE must be between 0 and 2")
if CONTENT_VERIFICATION_MAX_TOKENS < 64:
    raise ValueError("CONTENT_VERIFICATION_MAX_TOKENS must be at least 64")
if MAX_CONTENT_LENGTH < 1000:
    raise ValueError("MAX_CONTENT_LENGTH must be at least 1000 characters")
