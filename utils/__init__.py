"""
Utilities package for intelligent web scraping.
"""

from .scraper import IntelligentScraper, MAIN_LINK
from .link_classifier import LinkClassifier
from .api_key_manager import APIKeyManager, get_key_manager
from .course_analyzer import (
    fetch_html,
    make_soup,
    extract_manual_fields,
    classify_manual_page_type,
    ai_enrich_page,
    merge_results,
    write_csv,
    process_url,
    OUTPUT_CSV,
    CSV_COLUMNS,
)

__all__ = [
    # scraping pipeline
    'IntelligentScraper',
    'MAIN_LINK',
    # link classification
    'LinkClassifier',
    # API key management
    'APIKeyManager',
    'get_key_manager',
    # course analysis pipeline
    'fetch_html',
    'make_soup',
    'extract_manual_fields',
    'classify_manual_page_type',
    'ai_enrich_page',
    'merge_results',
    'write_csv',
    'process_url',
    'OUTPUT_CSV',
    'CSV_COLUMNS',
]
