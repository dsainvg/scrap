"""
AI-powered link classifier for intelligent web scraping.
Determines if links are back links or relevant to course pages.
Uses NVIDIA API for AI inference with multiple API key rotation.
"""

import os
import sys
import json
import time
import logging
import requests
from typing import Dict, List, Optional
from urllib.parse import urlparse
from dotenv import load_dotenv
from .api_key_manager import get_key_manager, APIKeyManager
from .link_extractor import extract_links_from_html

# Add setup to path for config import
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'setup'))
from setup.config import (
    LINK_CLASSIFICATION_MODEL,
    LINK_CLASSIFICATION_TEMPERATURE,
    LINK_CLASSIFICATION_MAX_TOKENS,
    LINK_CLASSIFICATION_TOP_P,
    CONTENT_VERIFICATION_MODEL,
    CONTENT_VERIFICATION_TEMPERATURE,
    CONTENT_VERIFICATION_MAX_TOKENS,
    CONTENT_VERIFICATION_TOP_P,
    BATCH_SIZE,
    BATCH_API_TIMEOUT,
    BATCH_INTER_DELAY,
    BATCH_MAX_RETRIES,
    NVIDIA_API_ENDPOINT,
    CLASSIFICATION_CACHE_FILE,
    MAX_CONTENT_LENGTH
)

# Load environment variables
load_dotenv()

# Set up logging
logger = logging.getLogger(__name__)

class LinkClassifier:
    """
    AI agent to classify links as back links or course-relevant links.
    Uses NVIDIA API with Qwen model and API key rotation for higher rate limits.
    """
    
    def __init__(self, model: str = None, use_key_rotation: bool = True, cache_file: str = None):
        """
        Initialize the link classifier with NVIDIA API.
        
        Args:
            model: NVIDIA model to use for classification (default: from config.LINK_CLASSIFICATION_MODEL)
            use_key_rotation: Use API key manager for rotation (default: True)
            cache_file: Path to cache file for storing processed links (default: from config.CLASSIFICATION_CACHE_FILE)
        """
        self.model = model or LINK_CLASSIFICATION_MODEL
        self.invoke_url = NVIDIA_API_ENDPOINT
        self.use_key_rotation = use_key_rotation
        self.cache_file = cache_file or CLASSIFICATION_CACHE_FILE
        
        # Initialize classification cache
        self.classification_cache: Dict[str, Dict] = {}
        self.cache_hits = 0
        self.cache_misses = 0
        self._load_cache()
        
        # Initialize API key manager
        if use_key_rotation:
            self.key_manager = get_key_manager()
            logger.info(f"Using API key rotation with {self.key_manager.get_key_count()} key(s)")
        else:
            # Fallback to single key
            single_key = os.getenv("NVIDIA_API_KEY")
            if not single_key:
                raise ValueError("NVIDIA API key not found. Set NVIDIA_API_KEY environment variable.")
            self.key_manager = None
            self.api_key = single_key
        
        # Load system prompt
        self.system_prompt = self._load_system_prompt()
    
    def _load_system_prompt(self) -> str:
        """Load system prompt from prompts/sys.txt"""
        prompt_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "prompts", "sys.txt")
        try:
            with open(prompt_path, 'r', encoding='utf-8') as f:
                return f.read().strip()
        except FileNotFoundError:
            logger.warning(f"System prompt file not found at {prompt_path}. Using default.")
            return self._get_default_prompt()
    
    def _get_default_prompt(self) -> str:
        """Default system prompt if file not found"""
        return """You are an intelligent link classifier for web scraping.
Your task is to analyze URLs and determine:
1. If a link is a "back link" (navigation back, parent pages, home, index)
2. If a link is a "course page" (specific individual course webpage with course code/name)
3. If a link is "course relevant" (course catalogs, listings, but not individual course pages)

Respond ONLY with a JSON object in this exact format:
{
    "is_back_link": true/false,
    "is_course_page": true/false,
    "is_course_relevant": true/false,
    "confidence": 0.0-1.0,
    "reasoning": "brief explanation"
}

Prioritize course pages (individual courses) over course-relevant (course lists)."""
    
    def _load_cache(self):
        """Load classification cache from file"""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    self.classification_cache = json.load(f)
                logger.info(f"Loaded {len(self.classification_cache)} cached classifications from {self.cache_file}")
            else:
                logger.info("No cache file found. Starting with empty cache.")
        except Exception as e:
            logger.warning(f"Failed to load cache: {str(e)}. Starting with empty cache.")
            self.classification_cache = {}
    
    def _save_cache(self):
        """Save classification cache to file"""
        try:
            cache_dir = os.path.dirname(os.path.abspath(self.cache_file))
            os.makedirs(cache_dir, exist_ok=True)
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.classification_cache, f, indent=2, ensure_ascii=False)
            logger.debug(f"Saved {len(self.classification_cache)} classifications to cache")
        except Exception as e:
            logger.error(f"Failed to save cache: {str(e)}")
    
    def _get_cache_key(self, url: str) -> str:
        """Generate cache key from URL (normalized)"""
        # Normalize URL for consistent caching
        from urllib.parse import urlparse, urlunparse
        parsed = urlparse(url)
        # Remove fragments and normalize
        normalized = urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, parsed.query, ''))
        return normalized.lower().strip()
    
    def _get_from_cache(self, url: str) -> Optional[Dict]:
        """Get classification result from cache"""
        cache_key = self._get_cache_key(url)
        if cache_key in self.classification_cache:
            self.cache_hits += 1
            logger.info(f"[OK] Cache HIT for: {url}")
            return self.classification_cache[cache_key]
        else:
            self.cache_misses += 1
            return None
    
    def _store_in_cache(self, url: str, result: Dict):
        """Store classification result in cache and save to file"""
        cache_key = self._get_cache_key(url)
        self.classification_cache[cache_key] = result
        # Save cache after every new API call result
        self._save_cache()
    
    def classify_link(self, url: str, context_url: str = None, link_text: str = None, html_context: Dict = None) -> Dict:
        """
        Classify a single link using AI.
        
        Args:
            url: The URL to classify
            context_url: The page where this link was found
            link_text: The anchor text or link description
            html_context: HTML blocks around the link for context
        
        Returns:
            Dictionary with classification results
        """
        # Check cache first
        cached_result = self._get_from_cache(url)
        if cached_result:
            # Add URL to cached result
            result = {**cached_result, 'url': url, 'from_cache': True}
            logger.debug(f"Using cached classification for: {url}")
            return result
        
        api_key = None
        try:
            # Prepare user message with context
            user_message = f"""Analyze this link:

URL: {url}
Link Text: {link_text or 'N/A'}
Found on page: {context_url or 'N/A'}"""

            # Add HTML context if available
            if html_context:
                if html_context.get('heading_above'):
                    user_message += f"\nHeading Above: {html_context['heading_above']}"
                
                if html_context.get('parent_text'):
                    parent_text = html_context['parent_text'][:150]  # Limit length
                    user_message += f"\nParent Block Text: {parent_text}"
                
                if html_context.get('parent_block'):
                    # Extract useful attributes from parent block
                    parent_preview = html_context['parent_block'][:200]
                    user_message += f"\nParent HTML (snippet): {parent_preview}"
            
            user_message += "\n\nClassify whether this is a back link, a course page, or course-relevant."
            
            # Get API key (with rotation if enabled)
            if self.use_key_rotation and self.key_manager:
                api_key = self.key_manager.get_next_key()
            else:
                api_key = self.api_key
            
            # Prepare NVIDIA API request
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Accept": "application/json"
            }
            
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user_message}
                ],
                "max_tokens": LINK_CLASSIFICATION_MAX_TOKENS,
                "temperature": LINK_CLASSIFICATION_TEMPERATURE,
                "top_p": LINK_CLASSIFICATION_TOP_P,
                "stream": False
            }
            
            # Call NVIDIA API
            response = requests.post(
                self.invoke_url,
                headers=headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            
            # Report success if using key manager
            if self.use_key_rotation and self.key_manager:
                self.key_manager.report_success(api_key)
            
            # Parse response
            response_data = response.json()
            content = response_data['choices'][0]['message']['content'].strip()
            
            # Extract JSON from response
            result = self._parse_classification_response(content)
            result['url'] = url
            result['from_cache'] = False
            
            # Store in cache
            self._store_in_cache(url, result)
            
            # Detailed logging of AI classification
            logger.info(f"\n{'='*80}")
            logger.info(f"AI CLASSIFICATION RESULT")
            logger.info(f"URL: {url}")
            logger.info(f"Link Text: {link_text or 'N/A'}")
            logger.info(f"Is Back Link: {result['is_back_link']}")
            logger.info(f"Is Course Page: {result.get('is_course_page', False)}")
            logger.info(f"Is Course Relevant: {result['is_course_relevant']}")
            logger.info(f"Confidence: {result.get('confidence', 0.0):.2f}")
            logger.info(f"Reasoning: {result.get('reasoning', 'N/A')}")
            logger.info(f"{'='*80}\n")
            
            return result
            
        except requests.exceptions.RequestException as e:
            logger.error(f"API request error for {url}: {str(e)}")
            
            # Report error if using key manager
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
        except Exception as e:
            logger.error(f"Error classifying link {url}: {str(e)}")
            # Return conservative fallback
            return {
                'url': url,
                'is_back_link': False,
                'is_course_page': False,
                'is_course_relevant': False,
                'confidence': 0.0,
                'reasoning': f'Error occurred: {str(e)}',
                'error': True
            }
    
    def classify_links_batch(self, links: List[Dict], context_url: str = None, batch_size: int = 10) -> List[Dict]:
        """
        Classify multiple links efficiently in batches using a single API call per batch.
        Checks cache first and only processes uncached links.
        
        Args:
            links: List of dictionaries with 'url' and optional 'text' and 'html_context' keys
            context_url: The page where these links were found
            batch_size: Number of links to process in each API call
        
        Returns:
            List of classification results
        """
        # STEP 1: Check cache for ALL links BEFORE any batch processing
        logger.info(f"Checking cache for {len(links)} links before batch processing...")
        
        all_results = []
        uncached_links = []
        uncached_indices = []
        
        for idx, link_info in enumerate(links):
            url = link_info.get('url')
            cached_result = self._get_from_cache(url)
            if cached_result:
                # Use cached result - no API call needed
                result = {**cached_result, 'url': url, 'from_cache': True}
                all_results.append((idx, result))
            else:
                # Need to process with AI
                uncached_links.append(link_info)
                uncached_indices.append(idx)
        
        # Log cache statistics
        cache_hit_count = len(all_results)
        cache_miss_count = len(uncached_links)
        logger.info(f"Cache check complete: {cache_hit_count} hits, {cache_miss_count} misses")
        
        if not uncached_links:
            # All links were cached - no API calls needed!
            logger.info("[OK] All links found in cache! No AI calls needed.")
            return [result for _, result in sorted(all_results)]
        
        # STEP 2: Process only uncached links in batches
        logger.info(f"Processing {cache_miss_count} uncached links in batches of {batch_size}...")
        
        # Process uncached links in batches
        for i in range(0, len(uncached_links), batch_size):
            batch = uncached_links[i:i+batch_size]
            batch_indices = uncached_indices[i:i+batch_size]
            logger.info(f"Processing batch {i//batch_size + 1}: {len(batch)} uncached links")

            # Delay between batches to avoid rate-limiting (skip before first batch)
            if i > 0:
                time.sleep(BATCH_INTER_DELAY)
            
            # Prepare batch message for AI
            batch_message = f"""Analyze these {len(batch)} links and classify each one:

Found on page: {context_url or 'N/A'}

Links to classify:
"""
            
            for idx, link_info in enumerate(batch, 1):
                url = link_info.get('url')
                text = link_info.get('text', 'N/A')
                html_context = link_info.get('html_context', {})
                
                batch_message += f"\n[Link {idx}]\n"
                batch_message += f"URL: {url}\n"
                batch_message += f"Text: {text}\n"
                
                if html_context.get('heading_above'):
                    batch_message += f"Heading Above: {html_context['heading_above']}\n"
                if html_context.get('parent_text'):
                    parent_text = html_context['parent_text'][:100]
                    batch_message += f"Context: {parent_text}\n"
            
            batch_message += f"""\nRespond with a JSON array of {len(batch)} objects, one for each link in order:
[
  {{"link": 1, "is_back_link": true/false, "is_course_page": true/false, "is_course_relevant": true/false, "confidence": 0.0-1.0, "reasoning": "brief explanation"}},
  {{"link": 2, ...}},
  ...
]"""
            
            try:
                # Get API key
                if self.use_key_rotation and self.key_manager:
                    api_key = self.key_manager.get_next_key()
                else:
                    api_key = self.api_key
                
                # Call API with retry-on-timeout
                last_exc = None
                response = None
                for attempt in range(1, BATCH_MAX_RETRIES + 2):  # +2: 1 initial + BATCH_MAX_RETRIES retries
                    try:
                        response = requests.post(
                            self.invoke_url,
                            headers={
                                "Authorization": f"Bearer {api_key}",
                                "Accept": "application/json"
                            },
                            json={
                                "model": self.model,
                                "messages": [
                                    {"role": "system", "content": self.system_prompt},
                                    {"role": "user", "content": batch_message}
                                ],
                                "max_tokens": LINK_CLASSIFICATION_MAX_TOKENS * 4,
                                "temperature": LINK_CLASSIFICATION_TEMPERATURE,
                                "top_p": LINK_CLASSIFICATION_TOP_P,
                                "stream": False
                            },
                            timeout=BATCH_API_TIMEOUT
                        )
                        response.raise_for_status()
                        break  # success
                    except requests.exceptions.Timeout as exc:
                        last_exc = exc
                        backoff = attempt * 5
                        logger.warning(f"Batch {i//batch_size + 1} timed out (attempt {attempt}/{BATCH_MAX_RETRIES + 1}). "
                                       f"Retrying in {backoff}s...")
                        time.sleep(backoff)
                    except requests.exceptions.RequestException as exc:
                        last_exc = exc
                        break  # non-timeout errors are not retried

                if response is None:
                    raise last_exc
                
                # Report success
                if self.use_key_rotation and self.key_manager:
                    self.key_manager.report_success(api_key)
                
                # Parse batch response
                content = response.json()['choices'][0]['message']['content'].strip()
                logger.info(f"\n{'='*80}")
                logger.info(f"AI BATCH RESPONSE (Batch {i//batch_size + 1}, {len(batch)} links)")
                logger.info(f"Raw Response:\n{content[:500]}..." if len(content) > 500 else f"Raw Response:\n{content}")
                logger.info(f"{'='*80}\n")
                
                batch_results = self._parse_batch_response(content, batch)
                
                # STEP 3: Store each result in cache immediately after API call
                logger.info(f"Saving {len(batch)} results to cache...")
                for idx, (link_info, result, orig_idx) in enumerate(zip(batch, batch_results, batch_indices), 1):
                    result['url'] = link_info['url']
                    result['from_cache'] = False
                    
                    # Store in cache (saves to file immediately)
                    self._store_in_cache(link_info['url'], result)
                    
                    all_results.append((orig_idx, result))
                
                logger.info(f"[OK] Saved batch results to cache file")
                
                # Log individual results from batch
                for idx, (link_info, result) in enumerate(zip(batch, batch_results), 1):
                    logger.info(f"  [{idx}] {link_info['url']}")
                    logger.info(f"      Back Link: {result.get('is_back_link', False)} | "
                               f"Course Page: {result.get('is_course_page', False)} | "
                               f"Course Relevant: {result.get('is_course_relevant', False)}")
                    logger.info(f"      Confidence: {result.get('confidence', 0.0):.2f} | "
                               f"Reasoning: {result.get('reasoning', 'N/A')[:80]}")
                    logger.info("")
                
            except Exception as e:
                logger.error(f"Batch classification error: {str(e)}")
                # Fallback: return conservative results for failed batch
                for link_info, orig_idx in zip(batch, batch_indices):
                    all_results.append((orig_idx, {
                        'url': link_info['url'],
                        'is_back_link': False,
                        'is_course_page': False,
                        'is_course_relevant': False,
                        'confidence': 0.0,
                        'reasoning': f'Batch error: {str(e)}',
                        'error': True,
                        'from_cache': False
                    }))
        
        # Sort results by original index and return just the results
        return [result for _, result in sorted(all_results)]
    
    def _parse_batch_response(self, response: str, batch: List[Dict]) -> List[Dict]:
        """Parse batch AI response into individual classification results"""
        try:
            # Find JSON array in response
            import json
            start_idx = response.find('[')
            end_idx = response.rfind(']') + 1
            
            if start_idx != -1 and end_idx > start_idx:
                json_str = response[start_idx:end_idx]
                results = json.loads(json_str)
                
                # Ensure we have the right number of results
                if len(results) == len(batch):
                    logger.info(f"Successfully parsed {len(results)} classifications from batch response")
                    # Normalize results to ensure all fields exist
                    normalized = []
                    for result in results:
                        normalized.append({
                            'is_back_link': result.get('is_back_link', False),
                            'is_course_page': result.get('is_course_page', False),
                            'is_course_relevant': result.get('is_course_relevant', False),
                            'confidence': result.get('confidence', 0.5),
                            'reasoning': result.get('reasoning', 'Batch classification')
                        })
                    return normalized
                else:
                    logger.warning(f"Result count mismatch: got {len(results)}, expected {len(batch)}")
            
            # Fallback: return default for all
            logger.warning("Failed to parse batch response, using defaults")
            return [{
                'is_back_link': False,
                'is_course_page': False,
                'is_course_relevant': False,
                'confidence': 0.0,
                'reasoning': 'Parse error'
            } for _ in batch]
            
        except Exception as e:
            logger.error(f"Batch response parsing error: {str(e)}")
            return [{
                'is_back_link': False,
                'is_course_page': False,
                'is_course_relevant': False,
                'confidence': 0.0,
                'reasoning': f'Parse error: {str(e)}'
            } for _ in batch]
    
    def find_course_pages_batch(self, links: List[Dict], context_url: str = None) -> Dict:
        """
        Specialized batch processing to find course pages from a list of links.
        Particularly useful for processing links from faculty teaching sections.
        
        Args:
            links: List of dictionaries with 'url' and optional 'text' keys
            context_url: The page where these links were found (e.g., faculty profile)
        
        Returns:
            Dictionary with categorized links emphasizing course_pages
        """
        course_pages = []
        course_relevant = []
        back_links = []
        irrelevant = []
        
        logger.info(f"Processing batch of {len(links)} links to find course pages")
        
        for link_info in links:
            url = link_info.get('url')
            text = link_info.get('text', '')
            html_context = link_info.get('html_context')
            
            # Quick heuristic for obvious non-course links
            if self.is_back_link_heuristic(url, text):
                back_links.append({**link_info, 'classification': 'back_link', 'method': 'heuristic'})
                continue
            
            # Check for course page indicators in URL/text
            if self._has_course_indicators(url, text):
                # Use AI to confirm it's a course page
                result = self.classify_link(url, context_url, text, html_context)
                
                if result.get('is_course_page'):
                    course_pages.append({**link_info, **result, 'classification': 'course_page'})
                elif result.get('is_course_relevant'):
                    course_relevant.append({**link_info, **result, 'classification': 'course_relevant'})
                elif result.get('is_back_link'):
                    back_links.append({**link_info, **result, 'classification': 'back_link'})
                else:
                    irrelevant.append({**link_info, **result, 'classification': 'irrelevant'})
            else:
                # Less likely to be course page, mark as irrelevant without AI
                irrelevant.append({**link_info, 'classification': 'irrelevant', 'method': 'heuristic'})
        
        return {
            'course_pages': course_pages,
            'course_relevant': course_relevant,
            'back_links': back_links,
            'irrelevant': irrelevant,
            'stats': {
                'total': len(links),
                'course_pages': len(course_pages),
                'course_relevant': len(course_relevant),
                'back_links': len(back_links),
                'irrelevant': len(irrelevant)
            }
        }
    
    def _has_course_indicators(self, url: str, text: str = '') -> bool:
        """
        Quick heuristic to check if URL or text suggests a course page.
        Looks for course codes, teaching keywords, etc.
        """
        url_lower = url.lower()
        text_lower = text.lower()
        
        # Course code patterns (CS101, MATH-202, etc.)
        import re
        course_code_pattern = r'\b[A-Z]{2,4}[-_\s]?\d{3,4}\b'
        if re.search(course_code_pattern, text, re.IGNORECASE):
            return True
        
        # URL patterns suggesting course pages
        course_url_patterns = [
            '/course/', '/courses/', '/teaching/', '/class/',
            'syllabus', 'curriculum', 'lecture', 'assignment',
            'fall', 'spring', 'summer', 'winter',  # semesters
            '/cs', '/math', '/phys', '/chem', '/bio',  # common dept prefixes
        ]
        
        if any(pattern in url_lower for pattern in course_url_patterns):
            # Additional check for text indicators
            course_text_patterns = [
                'course', 'class', 'lecture', 'syllabus',
                'fall', 'spring', 'semester', '2024', '2023', '2025'
            ]
            if any(pattern in text_lower for pattern in course_text_patterns):
                return True
        
        return False
    
    def _parse_classification_response(self, response: str) -> Dict:
        """Parse the AI response into structured data"""
        try:
            # Try to find JSON in the response
            start_idx = response.find('{')
            end_idx = response.rfind('}') + 1
            
            if start_idx != -1 and end_idx > start_idx:
                json_str = response[start_idx:end_idx]
                parsed = json.loads(json_str)
                # Ensure all expected fields exist
                if 'is_course_page' not in parsed:
                    parsed['is_course_page'] = False
                return parsed
            else:
                # Fallback parsing
                return {
                    'is_back_link': 'back' in response.lower() or 'navigation' in response.lower(),
                    'is_course_page': 'course page' in response.lower() or 'course_page' in response.lower(),
                    'is_course_relevant': 'course' in response.lower() and 'relevant' in response.lower(),
                    'confidence': 0.5,
                    'reasoning': 'Fallback parsing used'
                }
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse JSON from response: {response}")
            return {
                'is_back_link': False,
                'is_course_page': False,
                'is_course_relevant': False,
                'confidence': 0.0,
                'reasoning': 'Failed to parse AI response'
            }
    
    def is_back_link_heuristic(self, url: str, link_text: str = None) -> bool:
        """
        Quick heuristic check for back links without AI.
        Useful for obvious cases to save API calls.
        """
        url_lower = url.lower()
        text_lower = (link_text or '').lower()
        
        # Common back link patterns
        back_patterns = [
            'home', 'back', 'return', 'previous', 'parent',
            'index.html', 'index.php', '../', 'main',
            '?back', '&back'
        ]
        
        back_text_patterns = [
            'back', 'home', 'return', 'go back', '<-', '←',
            'previous page', 'main page', 'index'
        ]
        
        # Check URL
        if any(pattern in url_lower for pattern in back_patterns):
            return True
        
        # Check link text
        if any(pattern in text_lower for pattern in back_text_patterns):
            return True
        
        return False
    
    def filter_links(self, links: List[Dict], context_url: str = None, 
                    use_heuristics: bool = True, batch_size: int = None) -> Dict[str, List[Dict]]:
        """
        Filter links into categories: back_links, course_pages, course_relevant, and irrelevant.
        Uses batch processing for efficient AI classification.
        
        Args:
            links: List of link dictionaries
            context_url: The page where links were found
            use_heuristics: Use quick heuristics before AI classification
            batch_size: Number of links to process per AI request (default: from config.BATCH_SIZE)
        
        Returns:
            Dictionary with categorized links
        """
        # Use batch size from config if not specified
        if batch_size is None:
            batch_size = BATCH_SIZE
        
        # Deduplicate links by URL before processing (keep first occurrence with context)
        seen_urls = set()
        unique_links = []
        duplicates_found = 0
        for link_info in links:
            url = link_info.get('url')
            if url not in seen_urls:
                seen_urls.add(url)
                unique_links.append(link_info)
            else:
                duplicates_found += 1
        
        if duplicates_found > 0:
            logger.info(f"Removed {duplicates_found} duplicate URLs before classification (from {len(links)} to {len(unique_links)})")
        
        back_links = []
        course_pages = []
        course_relevant = []
        irrelevant = []
        
        # Separate links that can be filtered by heuristics
        needs_ai_classification = []
        
        for link_info in unique_links:
            url = link_info.get('url')
            text = link_info.get('text', '')
            
            # Quick heuristic check
            if use_heuristics and self.is_back_link_heuristic(url, text):
                back_links.append({**link_info, 'classification': 'back_link', 'method': 'heuristic'})
                logger.info(f"Filtered by heuristic (back link): {url}")
            else:
                # Needs AI classification
                needs_ai_classification.append(link_info)
        
        # Batch process links that need AI classification
        if needs_ai_classification:
            logger.info(f"Sending {len(needs_ai_classification)} links for batch AI classification")
            batch_results = self.classify_links_batch(needs_ai_classification, context_url, batch_size)
            
            # Categorize batch results
            for link_info, result in zip(needs_ai_classification, batch_results):
                combined = {**link_info, **result}
                
                if result.get('is_back_link'):
                    back_links.append({**combined, 'classification': 'back_link'})
                elif result.get('is_course_page') and result.get('confidence', 0) > 0.5:
                    course_pages.append({**combined, 'classification': 'course_page'})
                elif result.get('is_course_relevant') and result.get('confidence', 0) > 0.5:
                    course_relevant.append({**combined, 'classification': 'course_relevant'})
                else:
                    irrelevant.append({**combined, 'classification': 'irrelevant'})
        
        return {
            'back_links': back_links,
            'course_pages': course_pages,
            'course_relevant': course_relevant,
            'irrelevant': irrelevant,
            'stats': {
                'total': len(unique_links),  # Use deduplicated count
                'duplicates_removed': duplicates_found,
                'back_links': len(back_links),
                'course_pages': len(course_pages),
                'course_relevant': len(course_relevant),
                'irrelevant': len(irrelevant)
            }
        }
    
    def get_api_stats(self) -> Optional[dict]:
        """
        Get API key usage statistics if key rotation is enabled.
        
        Returns:
            Dictionary with API usage stats or None if rotation disabled
        """
        if self.use_key_rotation and self.key_manager:
            return self.key_manager.get_stats()
        return None
    
    def print_api_stats(self):
        """Print API key usage statistics"""
        if self.use_key_rotation and self.key_manager:
            self.key_manager.print_stats()
        else:
            logger.info("API key rotation is disabled. No stats available.")
    
    def get_cache_stats(self) -> Dict:
        """Get cache hit/miss statistics"""
        total = self.cache_hits + self.cache_misses
        hit_rate = (self.cache_hits / total * 100) if total > 0 else 0
        return {
            'cache_size': len(self.classification_cache),
            'cache_hits': self.cache_hits,
            'cache_misses': self.cache_misses,
            'hit_rate': hit_rate
        }
    
    def print_cache_stats(self):
        """Print cache statistics"""
        stats = self.get_cache_stats()
        logger.info(f"\n{'='*60}")
        logger.info("CLASSIFICATION CACHE STATISTICS")
        logger.info(f"{'='*60}")
        logger.info(f"Cache Size: {stats['cache_size']} entries")
        logger.info(f"Cache Hits: {stats['cache_hits']}")
        logger.info(f"Cache Misses: {stats['cache_misses']}")
        logger.info(f"Hit Rate: {stats['hit_rate']:.1f}%")
        logger.info(f"{'='*60}\n")
    
    def save_cache(self):
        """Manually save cache to file"""
        self._save_cache()
        logger.info(f"Cache saved to {self.cache_file}")
    
    def _load_content_analysis_prompt(self) -> str:
        """Load content analysis prompt from prompts/content_analysis.txt"""
        prompt_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "prompts", "content_analysis.txt")
        try:
            with open(prompt_path, 'r', encoding='utf-8') as f:
                return f.read().strip()
        except FileNotFoundError:
            logger.warning(f"Content analysis prompt file not found at {prompt_path}. Using default.")
            return """You are a content analyzer. Determine if webpage content is a course page and whether it contains links to other course pages.
Respond with JSON only: {"is_course_page": bool, "confidence": float, "course_code": str, "course_name": str, "semester": str, "reasoning": str, "has_other_course_links": bool}"""
    
    def _fetch_page_content(self, url: str, timeout: int = 10) -> Optional[str]:
        """
        Fetch the HTML content of a webpage.
        
        Args:
            url: URL to fetch
            timeout: Request timeout in seconds
        
        Returns:
            HTML content as string or None if failed
        """
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(url, headers=headers, timeout=timeout)
            response.raise_for_status()
            return response.text
        except Exception as e:
            logger.error(f"Failed to fetch content from {url}: {str(e)}")
            return None
    
    def _extract_text_from_html(self, html_content: str, max_length: int = None) -> str:
        """
        Extract meaningful text from HTML content for AI analysis.
        
        Args:
            html_content: Raw HTML content
            max_length: Maximum length of extracted text (default: from config.MAX_CONTENT_LENGTH)
        
        Returns:
            Cleaned text content
        """
        # Use max length from config if not specified
        if max_length is None:
            max_length = MAX_CONTENT_LENGTH
        
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style", "nav", "footer", "header"]):
                script.decompose()
            
            # Get text
            text = soup.get_text()
            
            # Clean up whitespace
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = ' '.join(chunk for chunk in chunks if chunk)
            
            # Truncate if too long
            if len(text) > max_length:
                text = text[:max_length] + "..."
            
            return text
        except Exception as e:
            logger.error(f"Failed to extract text from HTML: {str(e)}")
            return html_content[:max_length]
    
    def _extract_links_from_html_bs4(self, html_content: str, base_url: str) -> list:
        """
        Extract navigational anchor links from raw HTML.
        Delegates to the unified link_extractor.extract_links_from_html() so
        all extraction rules are applied consistently.
        Context is omitted here (include_context=False) because this method is
        called during content verification, where AI context hints are not needed.
        """
        return extract_links_from_html(html_content, base_url, include_context=False)

    def verify_course_page_content(self, url: str, content_model: str = None) -> Optional[Dict]:
        """
        Verify if a URL's actual content is a course page and extract course links.
        Uses a different model optimized for content analysis.
        
        Args:
            url: URL to verify
            content_model: NVIDIA model for content analysis (default: from config.CONTENT_VERIFICATION_MODEL)
        
        Returns:
            Dictionary with verification results and extracted course links, or None if failed
        """
        # Use content model from config if not specified
        if content_model is None:
            content_model = CONTENT_VERIFICATION_MODEL
        
        logger.info(f"Verifying course page content: {url}")
        
        # Fetch page content
        html_content = self._fetch_page_content(url)
        if not html_content:
            logger.error(f"Could not fetch content from {url}")
            return None
        
        # Extract text from HTML
        text_content = self._extract_text_from_html(html_content)
        logger.info(f"Extracted {len(text_content)} characters from {url}")
        
        # Load content analysis prompt
        content_prompt = self._load_content_analysis_prompt()
        
        # Prepare user message with content snippet
        user_message = f"""Analyze this webpage content and determine if it's a course page.

URL: {url}

Content (first 8000 chars):
{text_content}

Respond with JSON only."""
        
        # Make API call with content analysis model
        api_key = None
        try:
            # Get API key
            if self.use_key_rotation:
                api_key = self.key_manager.get_next_key()
            else:
                api_key = self.api_key
            
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": content_model,
                "messages": [
                    {"role": "system", "content": content_prompt},
                    {"role": "user", "content": user_message}
                ],
                "temperature": CONTENT_VERIFICATION_TEMPERATURE,
                "max_tokens": CONTENT_VERIFICATION_MAX_TOKENS,
                "top_p": CONTENT_VERIFICATION_TOP_P
            }
            
            response = requests.post(self.invoke_url, headers=headers, json=payload)
            response.raise_for_status()
            
            # Record successful API call
            if self.use_key_rotation:
                self.key_manager.report_success(api_key)
            
            # Parse response
            result = response.json()
            content = result['choices'][0]['message']['content'].strip()
            
            # Extract JSON from response
            try:
                # Try to find JSON in response
                if '```json' in content:
                    json_str = content.split('```json')[1].split('```')[0].strip()
                elif '```' in content:
                    json_str = content.split('```')[1].split('```')[0].strip()
                else:
                    json_str = content
                
                verification_result = json.loads(json_str)
                logger.info(f"Content verification: is_course_page={verification_result.get('is_course_page')}, "
                          f"confidence={verification_result.get('confidence')}, "
                          f"has_other_course_links={verification_result.get('has_other_course_links')}")

                # Use BeautifulSoup to extract links if AI detected course links are present
                if verification_result.get('has_other_course_links'):
                    extracted_links = self._extract_links_from_html_bs4(html_content, url)
                    verification_result['course_links_found'] = extracted_links
                    logger.info(f"BS4 extracted {len(extracted_links)} candidate links from {url}")
                else:
                    verification_result['course_links_found'] = []

                return verification_result
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON response: {content[:200]}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed for content verification: {str(e)}")
            if self.use_key_rotation and api_key:
                self.key_manager.report_error(api_key)
            return None
        except Exception as e:
            logger.error(f"Unexpected error in content verification: {str(e)}")
            return None
