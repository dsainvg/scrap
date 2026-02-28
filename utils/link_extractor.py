"""
Unified, robust link extraction utilities.

Both the scraper (extract_all_links) and the link classifier
(_extract_links_from_html_bs4) previously had separate, diverging logic.
This module is the single source of truth for anchor-link extraction.

Rules applied by extract_links_from_html():
  1.  Only <a href="..."> tags — navigational links, not resource tags.
  2.  Skip empty / whitespace-only hrefs.
  3.  Skip fragment-only hrefs (e.g. href="#section").
  4.  Skip javascript:, mailto:, tel:, ftp:, data:, blob: schemes.
  5.  Resolve relative URLs via urljoin against the page's base URL.
  6.  Keep only http / https final URLs.
  7.  Skip static file links (images, PDFs, archives, media, CSS/JS, etc.)
      but KEEP web-page extensions (.html, .htm, .php, .asp, .aspx, .jsp, .do).
  8.  Deduplicate — scheme-normalised (http->https) + trailing-slash stripped.
"""

import re
import logging
from typing import Dict, List, Union
from urllib.parse import urljoin, urlparse

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Extension sets
# ---------------------------------------------------------------------------

# These extensions indicate static files that are never course web pages.
FILE_EXTENSIONS: List[str] = [
    # Images
    '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.ico', '.webp', '.tiff', '.tif',
    # Documents
    '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.odt', '.ods', '.odp',
    # Archives
    '.zip', '.rar', '.tar', '.gz', '.7z', '.bz2', '.xz',
    # Media
    '.mp4', '.mp3', '.avi', '.mov', '.wmv', '.flv', '.wav', '.mkv', '.webm',
    # Code / data (non-navigational)
    '.css', '.js', '.json', '.xml', '.txt', '.csv', '.sql', '.log',
    # E-book / print
    '.epub', '.mobi', '.azw', '.djvu', '.ps', '.eps',
]

# These extensions are web pages and must NEVER be treated as file links.
WEB_EXTENSIONS: List[str] = [
    '.html', '.htm', '.php', '.asp', '.aspx', '.jsp', '.do',
]

# Raw href prefixes / substrings that are immediately invalid.
_SKIP_SCHEMES = (
    'javascript:',
    'mailto:',
    'tel:',
    'ftp:',
    'data:',
    'blob:',
    'void(',
)

# URL tokens that strongly suggest a direct-download link.
_DOWNLOAD_TOKENS = ('download', 'attachment', 'file=')


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

def is_file_link(url: str) -> bool:
    """
    Return True if *url* points to a static file rather than a web page.

    Web-page extensions (.html, .htm, .php, .asp, .aspx, .jsp, .do) always
    return False — they are navigable pages regardless of anything else.
    """
    parsed = urlparse(url.lower())
    path = parsed.path

    # Web-page extensions are never file links.
    if any(path.endswith(ext) for ext in WEB_EXTENSIONS):
        return False

    # Exact known file extension match.
    if any(path.endswith(ext) for ext in FILE_EXTENSIONS):
        return True

    # Download / attachment indicator anywhere in the URL.
    if any(token in url.lower() for token in _DOWNLOAD_TOKENS):
        return True

    return False


def extract_html_context(element) -> Dict[str, str]:
    """
    Extract surrounding HTML context for a BeautifulSoup anchor element.

    Returns a dict useful as an AI classification hint:
        parent_block    – the nearest block-level parent's HTML (≤ 500 chars)
        parent_text     – that parent's plain text (≤ 200 chars)
        previous_block  – previous sibling block's HTML (≤ 300 chars)
        heading_above   – nearest heading tag text above the link
    """
    context: Dict[str, str] = {
        'parent_block': '',
        'previous_block': '',
        'parent_text': '',
        'heading_above': '',
    }
    try:
        parent = element.find_parent(
            ['div', 'section', 'article', 'li', 'td', 'tr', 'ul', 'ol']
        )
        if parent:
            context['parent_block'] = str(parent)[:500]
            context['parent_text'] = parent.get_text(strip=True)[:200]
            prev = parent.find_previous_sibling(
                ['div', 'section', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p']
            )
            if prev:
                context['previous_block'] = str(prev)[:300]

        heading = element.find_previous(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
        if heading:
            context['heading_above'] = heading.get_text(strip=True)

    except Exception as exc:
        logger.debug(f"extract_html_context error: {exc}")

    return context


def extract_links_from_html(
    html_content: str,
    base_url: str,
    include_context: bool = True,
    _soup=None,
) -> List[Dict]:
    """
    Extract all navigational anchor links from *html_content*.

    This is the single unified implementation used by both the scraper and
    the link classifier.  All eight rules listed at the top of this module
    are enforced here.

    Args:
        html_content:    Raw HTML string of the page.
        base_url:        URL the page was fetched from (used for resolving
                         relative hrefs and stored as 'source_url').
        include_context: When True, each result dict includes an
                         'html_context' key with surrounding DOM context
                         (useful for AI classification).  Disable for speed
                         when context is not needed.

    Returns:
        List of dicts with keys:
            url          – absolute, resolved URL
            text         – visible anchor text
            title        – <a title="..."> attribute (may be empty)
            source_url   – the page URL being parsed (= base_url)
            tag          – always 'a'
            html_context – dict from extract_html_context() (or {} if disabled)
    """
    from bs4 import BeautifulSoup

    if _soup is not None:
        soup = _soup
    else:
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
        except Exception as exc:
            logger.error(f"BeautifulSoup parse error for {base_url}: {exc}")
            return []

    links: List[Dict] = []
    seen: set = set()

    for anchor in soup.find_all('a', href=True):
        href: str = anchor.get('href', '').strip()

        # Rule 2 – skip empty hrefs.
        if not href:
            continue

        # Rule 3 – skip fragment-only hrefs.
        if href.startswith('#'):
            continue

        # Rule 4 – skip invalid / non-navigational schemes.
        href_lower = href.lower()
        if any(href_lower.startswith(s) for s in _SKIP_SCHEMES):
            continue

        # Rule 5 – resolve to absolute URL.
        full_url = urljoin(base_url, href)

        # Rule 6 – keep only http / https.
        parsed = urlparse(full_url)
        if parsed.scheme not in ('http', 'https'):
            continue

        # Strip fragment from final URL – fragments point to an anchor within the
        # same page (e.g. dynamic.html and dynamic.html#1ddyn are the same resource).
        if parsed.fragment:
            from urllib.parse import urlunparse
            full_url = urlunparse((
                parsed.scheme, parsed.netloc, parsed.path,
                parsed.params, parsed.query, ''
            ))
            parsed = urlparse(full_url)  # re-parse without fragment

        # Rule 7 – skip static file links.
        if is_file_link(full_url):
            continue

        # Rule 8 – deduplicate using scheme-normalised URL (fragment already stripped).
        normalised = parsed._replace(scheme='https').geturl().rstrip('/')
        if normalised in seen:
            continue
        seen.add(normalised)

        # Collect per-link metadata.
        text: str = anchor.get_text(strip=True)
        title: str = anchor.get('title', '').strip()
        html_context: Dict = extract_html_context(anchor) if include_context else {}

        links.append({
            'url': full_url,
            'text': text,
            'title': title,
            'source_url': base_url,
            'tag': 'a',
            'html_context': html_context,
        })

    logger.debug(f"extract_links_from_html: {len(links)} links from {base_url}")
    return links
