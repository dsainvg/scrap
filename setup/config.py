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

# Validate settings
if SCRAPER_TIMEOUT < 1:
    raise ValueError("SCRAPER_TIMEOUT must be at least 1 second")
if SCRAPER_DELAY < 0:
    raise ValueError("SCRAPER_DELAY cannot be negative")
if MAX_SCRAPING_DEPTH < 1:
    raise ValueError("MAX_SCRAPING_DEPTH must be at least 1")
