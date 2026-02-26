"""
Intelligent web scraper that extracts links and filters them using AI classification.
"""

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import logging
from typing import List, Dict, Set
import time
from .link_classifier import LinkClassifier
from setup.config import SCRAPER_TIMEOUT, SCRAPER_DELAY, MAX_SCRAPING_DEPTH

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/scraper.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Constants
# Direct link to faculty data (loaded via AJAX on the main page)
MAIN_LINK = "https://cse.iitkgp.ac.in/faculty4.php"


class IntelligentScraper:
    """
    Web scraper that extracts all links from pages and uses AI to filter relevant course links.
    """
    
    def __init__(self, base_url: str, use_ai_classification: bool = True, save_interval: int = 200, output_file: str = 'data/scraped_links.json'):
        """
        Initialize the intelligent scraper.
        
        Args:
            base_url: The starting URL to scrape
            use_ai_classification: Whether to use AI for link classification
            save_interval: Save results every N links processed (default: 200)
            output_file: Path to save results (default: data/scraped_links.json)
        """
        self.base_url = base_url
        self.domain = urlparse(base_url).netloc
        self.visited_urls: Set[str] = set()
        self.all_extracted_links: List[Dict] = []  # ALL links extracted
        self.external_links: List[Dict] = []  # External domain links
        self.course_pages: List[Dict] = []  # Individual course pages
        self.course_relevant_links: List[Dict] = []  # Course lists/catalogs
        self.back_links: List[Dict] = []
        self.irrelevant_links: List[Dict] = []
        self.file_links: List[Dict] = []  # File resources (PDFs, images, etc.)
        
        # Periodic save settings
        self.save_interval = save_interval
        self.output_file = output_file
        self.links_processed_since_save = 0
        self.total_links_processed = 0
        
        # Initialize AI classifier if enabled
        self.use_ai = use_ai_classification
        self.classifier = LinkClassifier() if use_ai_classification else None
        
        # Session for connection pooling
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def _extract_html_context(self, element) -> Dict[str, str]:
        """
        Extract HTML context around an element for better AI classification.
        
        Args:
            element: BeautifulSoup element (typically an anchor tag)
        
        Returns:
            Dictionary with HTML context blocks
        """
        context = {
            'parent_block': '',
            'previous_block': '',
            'parent_text': '',
            'heading_above': ''
        }
        
        try:
            # Get parent block (div, section, article, li, td, etc.)
            parent = element.find_parent(['div', 'section', 'article', 'li', 'td', 'tr', 'ul', 'ol'])
            if parent:
                # Get parent's HTML (limit to 500 chars to avoid too much context)
                parent_html = str(parent)[:500]
                context['parent_block'] = parent_html
                # Get parent's text content
                context['parent_text'] = parent.get_text(strip=True)[:200]
            
            # Get previous sibling block
            if parent:
                prev_sibling = parent.find_previous_sibling(['div', 'section', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p'])
                if prev_sibling:
                    context['previous_block'] = str(prev_sibling)[:300]
            
            # Find nearest heading above the link
            heading = element.find_previous(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
            if heading:
                context['heading_above'] = heading.get_text(strip=True)
        
        except Exception as e:
            logger.debug(f"Error extracting HTML context: {str(e)}")
        
        return context
    
    def extract_all_links(self, url: str) -> List[Dict]:
        """
        Extract all links from a given URL.
        
        Args:
            url: The URL to scrape
        
        Returns:
            List of dictionaries containing link information
        """
        try:
            logger.info(f"Fetching: {url}")
            response = self.session.get(url, timeout=SCRAPER_TIMEOUT)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            links = []
            seen_urls = set()  # Track unique URLs
            
            # Extract ALL anchor tags with href
            for anchor in soup.find_all('a', href=True):
                href = anchor.get('href', '').strip()
                if not href:
                    continue
                    
                text = anchor.get_text(strip=True)
                title = anchor.get('title', '')
                
                # Resolve relative URLs
                absolute_url = urljoin(url, href)
                
                # Skip anchors and javascript
                if absolute_url.startswith('#') or absolute_url.startswith('javascript:'):
                    continue
                
                if absolute_url not in seen_urls:
                    seen_urls.add(absolute_url)
                    
                    # Extract HTML context for better AI classification
                    html_context = self._extract_html_context(anchor)
                    
                    links.append({
                        'url': absolute_url,
                        'text': text,
                        'title': title,
                        'source_url': url,
                        'tag': 'a',
                        'html_context': html_context
                    })
            
            # Extract links from <link> tags (stylesheets, icons, preload, etc.)
            # Skip stylesheets
            for link_tag in soup.find_all('link', href=True):
                href = link_tag.get('href', '').strip()
                if href:
                    # Skip stylesheets
                    rel = link_tag.get('rel', [])
                    if isinstance(rel, list) and 'stylesheet' in rel:
                        continue
                    if isinstance(rel, str) and rel == 'stylesheet':
                        continue
                    # Skip CSS files by extension
                    if href.lower().endswith('.css') or '.css?' in href.lower():
                        continue
                    
                    absolute_url = urljoin(url, href)
                    if absolute_url not in seen_urls and not absolute_url.startswith('javascript:'):
                        seen_urls.add(absolute_url)
                        links.append({
                            'url': absolute_url,
                            'text': link_tag.get('rel', [''])[0] if isinstance(link_tag.get('rel'), list) else link_tag.get('rel', ''),
                            'title': link_tag.get('type', ''),
                            'source_url': url,
                            'tag': 'link'
                        })
            
            # Extract links from <img> tags
            for img in soup.find_all('img', src=True):
                src = img.get('src', '').strip()
                if src:
                    absolute_url = urljoin(url, src)
                    if absolute_url not in seen_urls:
                        seen_urls.add(absolute_url)
                        links.append({
                            'url': absolute_url,
                            'text': img.get('alt', ''),
                            'title': img.get('title', ''),
                            'source_url': url,
                            'tag': 'img'
                        })
            
            # Extract links from <script> tags
            # Skip JavaScript files - not relevant for course content
            # Uncomment below if you want to extract script files
            # for script in soup.find_all('script', src=True):
            #     src = script.get('src', '').strip()
            #     if src:
            #         absolute_url = urljoin(url, src)
            #         if absolute_url not in seen_urls and not absolute_url.startswith('javascript:'):
            #             seen_urls.add(absolute_url)
            #             links.append({
            #                 'url': absolute_url,
            #                 'text': '',
            #                 'title': script.get('type', ''),
            #                 'source_url': url,
            #                 'tag': 'script'
            #             })
            
            # Extract links from <iframe> tags
            for iframe in soup.find_all('iframe', src=True):
                src = iframe.get('src', '').strip()
                if src:
                    absolute_url = urljoin(url, src)
                    if absolute_url not in seen_urls and not absolute_url.startswith('javascript:'):
                        seen_urls.add(absolute_url)
                        links.append({
                            'url': absolute_url,
                            'text': iframe.get('title', ''),
                            'title': iframe.get('name', ''),
                            'source_url': url,
                            'tag': 'iframe'
                        })
            
            # Extract links from <area> tags (image maps)
            for area in soup.find_all('area', href=True):
                href = area.get('href', '').strip()
                if href:
                    absolute_url = urljoin(url, href)
                    if absolute_url not in seen_urls and not absolute_url.startswith('javascript:'):
                        seen_urls.add(absolute_url)
                        links.append({
                            'url': absolute_url,
                            'text': area.get('alt', ''),
                            'title': area.get('title', ''),
                            'source_url': url,
                            'tag': 'area'
                        })
            
            # Extract links from <form> action attributes
            for form in soup.find_all('form', action=True):
                action = form.get('action', '').strip()
                if action:
                    absolute_url = urljoin(url, action)
                    if absolute_url not in seen_urls and not absolute_url.startswith('javascript:'):
                        seen_urls.add(absolute_url)
                        links.append({
                            'url': absolute_url,
                            'text': form.get('name', ''),
                            'title': form.get('method', 'GET'),
                            'source_url': url,
                            'tag': 'form'
                        })
            
            # Extract links from <base> tag
            base_tag = soup.find('base', href=True)
            if base_tag:
                href = base_tag.get('href', '').strip()
                if href:
                    absolute_url = urljoin(url, href)
                    if absolute_url not in seen_urls:
                        seen_urls.add(absolute_url)
                        links.append({
                            'url': absolute_url,
                            'text': 'base',
                            'title': '',
                            'source_url': url,
                            'tag': 'base'
                        })
            
            # Extract links from <video> and <audio> tags
            for media in soup.find_all(['video', 'audio', 'source'], src=True):
                src = media.get('src', '').strip()
                if src:
                    absolute_url = urljoin(url, src)
                    if absolute_url not in seen_urls:
                        seen_urls.add(absolute_url)
                        links.append({
                            'url': absolute_url,
                            'text': media.get('title', ''),
                            'title': media.name,
                            'source_url': url,
                            'tag': media.name
                        })
            
            # Extract links from <embed> and <object> tags
            for embed in soup.find_all(['embed', 'object'], {'src': True, 'data': True}):
                src = embed.get('src') or embed.get('data', '').strip()
                if src:
                    absolute_url = urljoin(url, src)
                    if absolute_url not in seen_urls:
                        seen_urls.add(absolute_url)
                        links.append({
                            'url': absolute_url,
                            'text': embed.get('title', ''),
                            'title': embed.get('type', ''),
                            'source_url': url,
                            'tag': embed.name
                        })
            
            # Log extracted links clearly
            logger.info(f"\n{'='*80}")
            logger.info(f"EXTRACTED {len(links)} TOTAL LINKS FROM: {url}")
            logger.info(f"{'='*80}")
            
            # Group by tag type for clear output
            by_tag = {}
            for link in links:
                tag = link['tag']
                if tag not in by_tag:
                    by_tag[tag] = []
                by_tag[tag].append(link)
            
            # Print links by category
            for tag, tag_links in sorted(by_tag.items()):
                logger.info(f"\n[{tag.upper()}] - {len(tag_links)} links:")
                for link in tag_links:  # Show all links
                    text_preview = link['text'][:50] if link['text'] else '(no text)'
                    logger.info(f"  -> {link['url']}")
                    if link['text']:
                        logger.info(f"     Text: {text_preview}")
            
            logger.info(f"\n{'='*80}")
            logger.info(f"SUMMARY: {sum(1 for l in links if l['tag'] == 'a')} anchors, {sum(1 for l in links if l['tag'] != 'a')} resources")
            logger.info(f"{'='*80}\n")
            
            return links
            
        except requests.RequestException as e:
            logger.error(f"Error fetching {url}: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error extracting links from {url}: {str(e)}")
            return []
    
    def is_same_domain(self, url: str) -> bool:
        """Check if URL belongs to the same domain"""
        return urlparse(url).netloc == self.domain
    
    def _periodic_save(self):
        """Save current scraping results to file (periodic checkpoint)"""
        try:
            self.save_results(output_file=self.output_file)
            logger.info(f"✓ Progress saved to {self.output_file}")
        except Exception as e:
            logger.error(f"Failed to save periodic checkpoint: {str(e)}")
    
    def is_file_link(self, url: str) -> bool:
        """Check if URL points to a file (image, PDF, video, etc.)"""
        # Common file extensions that should not be checked by AI
        file_extensions = [
            # Images
            '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.ico', '.webp', '.tiff', '.tif',
            # Documents
            '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.odt', '.ods', '.odp',
            # Archives
            '.zip', '.rar', '.tar', '.gz', '.7z', '.bz2', '.xz',
            # Media
            '.mp4', '.mp3', '.avi', '.mov', '.wmv', '.flv', '.wav', '.mkv', '.webm',
            # Code/Data
            '.css', '.js', '.json', '.xml', '.txt', '.csv', '.sql', '.log',
            # Other
            '.epub', '.mobi', '.azw', '.djvu', '.ps', '.eps'
        ]
        
        # Parse URL and get the path
        parsed = urlparse(url.lower())
        path = parsed.path
        
        # Check if the path ends with any file extension
        for ext in file_extensions:
            if path.endswith(ext):
                return True
        
        # Check for query string parameters that indicate files
        if any(ext in path for ext in file_extensions):
            return True
        
        # Check for files with dots followed by extension-like patterns (e.g., document.pdf, file.xyz)
        # Look for pattern: /something.ext or /path/file.ext at the end
        import re
        # Match URLs that end with filename.extension pattern
        file_pattern = r'/[^/]+\.[a-zA-Z0-9]{2,4}$'
        if re.search(file_pattern, path):
            # Additional check: make sure it's not a common web page extension
            web_extensions = ['.html', '.htm', '.php', '.asp', '.aspx', '.jsp', '.do']
            if not any(path.endswith(ext) for ext in web_extensions):
                return True
        
        # Check for download links or file attachments in query params
        if 'download' in url.lower() or 'attachment' in url.lower() or 'file=' in url.lower():
            return True
        
        return False
    
    def scrape_page(self, url: str, max_depth: int = 2, current_depth: int = 0):
        """
        Scrape a page and recursively follow course-relevant links.
        
        Args:
            url: The URL to scrape
            max_depth: Maximum depth for recursive scraping
            current_depth: Current recursion depth
        """
        # Check if already visited
        if url in self.visited_urls:
            logger.debug(f"Already visited: {url}")
            return
        
        # Check depth limit
        if current_depth > max_depth:
            logger.debug(f"Max depth reached for: {url}")
            return
        
        # Mark as visited
        self.visited_urls.add(url)
        
        # Extract all links from the page
        extracted_links = self.extract_all_links(url)
        
        if not extracted_links:
            return
        
        # Store ALL extracted links
        self.all_extracted_links.extend(extracted_links)
        
        # Separate same-domain and external links
        same_domain_links = []
        external_links = []
        
        for link in extracted_links:
            if self.is_same_domain(link['url']):
                same_domain_links.append(link)
            else:
                external_links.append(link)
        
        # Store external links
        self.external_links.extend(external_links)
        
        logger.info(f"Found {len(same_domain_links)} same-domain links, {len(external_links)} external links")
        
        # Separate file links from web page links
        file_links = []
        web_page_links = []
        
        for link in same_domain_links:
            if self.is_file_link(link['url']):
                # Add parent folder context
                link['parent_folder'] = url
                link['parent_depth'] = current_depth
                file_links.append(link)
            else:
                web_page_links.append(link)
        
        if file_links:
            logger.info(f"Found {len(file_links)} file links (images, PDFs, etc.) - storing with parent context")
            # Store file links separately with parent folder information
            self.file_links.extend(file_links)
        
        # Classify links using AI (only web page links, not files)
        if self.use_ai and self.classifier and web_page_links:
            logger.info(f"Classifying {len(web_page_links)} web page links with AI")
            classified = self.classifier.filter_links(web_page_links, context_url=url)
            
            # Store classified links
            self.back_links.extend(classified['back_links'])
            self.course_pages.extend(classified.get('course_pages', []))
            self.course_relevant_links.extend(classified['course_relevant'])
            self.irrelevant_links.extend(classified['irrelevant'])
            
            # Update link processing counter
            links_classified = len(web_page_links)
            self.links_processed_since_save += links_classified
            self.total_links_processed += links_classified
            
            # Periodic save every N links
            if self.links_processed_since_save >= self.save_interval:
                logger.info(f"\n{'='*60}")
                logger.info(f"PERIODIC SAVE: {self.total_links_processed} links processed")
                logger.info(f"{'='*60}")
                self._periodic_save()
                self.links_processed_since_save = 0
            
            # Log classification stats
            stats = classified['stats']
            logger.info(f"Classification: {stats['course_pages']} course pages, "
                       f"{stats['course_relevant']} course-relevant, "
                       f"{stats['back_links']} back links, "
                       f"{stats['irrelevant']} irrelevant")
            
            # Recursively scrape ONLY course-relevant links (catalogs, listings, faculty pages)
            # DO NOT recurse into course pages (they are end goals) or irrelevant links
            if current_depth < max_depth:
                logger.info(f"Recursion enabled. Current depth: {current_depth}/{max_depth}")
                
                # Only follow course-relevant links (catalogs, listings, faculty pages)
                # These pages may contain course pages, so we need to explore them
                for link_info in classified['course_relevant']:
                    next_url = link_info['url']
                    if next_url not in self.visited_urls:
                        logger.info(f"Following course-relevant link: {next_url}")
                        time.sleep(SCRAPER_DELAY)  # Rate limiting
                        self.scrape_page(next_url, max_depth, current_depth + 1)
                
                # DO NOT recurse into course pages - they are the final destination
                course_page_count = len(classified.get('course_pages', []))
                if course_page_count > 0:
                    logger.info(f"Found {course_page_count} course page(s) - NOT recursing (end goals reached)")
                
                # DO NOT recurse into irrelevant or back links - save time and API calls
                irrelevant_count = len(classified['irrelevant'])
                back_link_count = len(classified['back_links'])
                if irrelevant_count > 0:
                    logger.info(f"Skipping {irrelevant_count} irrelevant link(s) - NOT recursing")
                if back_link_count > 0:
                    logger.info(f"Skipping {back_link_count} back link(s) - NOT recursing")
        elif web_page_links:
            # Without AI, just collect web page links (files are already in irrelevant)
            logger.info(f"AI classification disabled. Collected {len(web_page_links)} web page links")
            self.course_relevant_links.extend(web_page_links)
    
    def scrape(self, max_depth: int = 2) -> Dict:
        """
        Start the scraping process.
        
        Args:
            max_depth: Maximum depth for recursive scraping
        
        Returns:
            Dictionary with scraping results
        """
        logger.info(f"Starting intelligent scrape from: {self.base_url}")
        logger.info(f"Max depth: {max_depth}, AI classification: {self.use_ai}")
        
        # Start scraping from base URL
        self.scrape_page(self.base_url, max_depth=max_depth)
        
        # Compile results
        results = {
            'base_url': self.base_url,
            'visited_urls': list(self.visited_urls),
            'all_extracted_links': self.all_extracted_links,
            'external_links': self.external_links,
            'course_pages': self.course_pages,
            'course_relevant_links': self.course_relevant_links,
            'back_links': self.back_links,
            'irrelevant_links': self.irrelevant_links,
            'file_links': self.file_links,
            'stats': {
                'total_visited': len(self.visited_urls),
                'total_links_extracted': len(self.all_extracted_links),
                'external_links': len(self.external_links),
                'same_domain_links': len(self.all_extracted_links) - len(self.external_links),
                'course_pages': len(self.course_pages),
                'course_relevant': len(self.course_relevant_links),
                'back_links': len(self.back_links),
                'irrelevant': len(self.irrelevant_links),
                'file_links': len(self.file_links)
            }
        }
        
        logger.info(f"Scraping complete. Stats: {results['stats']}")
        return results
    
    def get_unique_course_links(self) -> List[str]:
        """Get unique course page URLs (prioritized)"""
        return list(set(link['url'] for link in self.course_pages))
    
    def get_unique_course_relevant_links(self) -> List[str]:
        """Get unique course-relevant URLs (catalogs, listings)"""
        return list(set(link['url'] for link in self.course_relevant_links))
    
    def save_results(self, output_file: str = 'data/scraped_links.json'):
        """Save scraping results to a JSON file"""
        import json
        import os
        
        results = {
            'base_url': self.base_url,
            'visited_urls': list(self.visited_urls),
            'all_extracted_links': self.all_extracted_links,
            'external_links': self.external_links,
            'course_pages': self.course_pages,
            'course_relevant_links': self.course_relevant_links,
            'back_links': self.back_links,
            'irrelevant_links': self.irrelevant_links,
            'file_links': self.file_links,
            'stats': {
                'total_visited': len(self.visited_urls),
                'total_links_extracted': len(self.all_extracted_links),
                'external_links': len(self.external_links),
                'same_domain_links': len(self.all_extracted_links) - len(self.external_links),
                'course_pages': len(self.course_pages),
                'course_relevant': len(self.course_relevant_links),
                'back_links': len(self.back_links),
                'irrelevant': len(self.irrelevant_links),
                'file_links': len(self.file_links)
            }
        }
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Results saved to: {output_file}")
        return output_file

