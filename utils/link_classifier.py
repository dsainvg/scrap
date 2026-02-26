"""
AI-powered link classifier for intelligent web scraping.
Determines if links are back links or relevant to course pages.
Uses NVIDIA API for AI inference with multiple API key rotation.
"""

import os
import json
import logging
import requests
from typing import Dict, List, Optional
from urllib.parse import urlparse
from dotenv import load_dotenv
from .api_key_manager import get_key_manager, APIKeyManager

# Load environment variables
load_dotenv()

# Set up logging
logger = logging.getLogger(__name__)

class LinkClassifier:
    """
    AI agent to classify links as back links or course-relevant links.
    Uses NVIDIA API with Qwen model and API key rotation for higher rate limits.
    """
    
    def __init__(self, model: str = "qwen/qwen3.5-397b-a17b", use_key_rotation: bool = True):
        """
        Initialize the link classifier with NVIDIA API.
        
        Args:
            model: NVIDIA model to use for classification (default: qwen/qwen3.5-397b-a17b)
            use_key_rotation: Use API key manager for rotation (default: True)
        """
        self.model = model
        self.invoke_url = "https://integrate.api.nvidia.com/v1/chat/completions"
        self.use_key_rotation = use_key_rotation
        
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
                "max_tokens": 512,
                "temperature": 0.20,
                "top_p": 0.70,
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
            if self.use_key_rotation and self.key_manager:
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
        
        Args:
            links: List of dictionaries with 'url' and optional 'text' and 'html_context' keys
            context_url: The page where these links were found
            batch_size: Number of links to process in each API call
        
        Returns:
            List of classification results
        """
        all_results = []
        
        # Process links in batches
        for i in range(0, len(links), batch_size):
            batch = links[i:i+batch_size]
            logger.info(f"Processing batch {i//batch_size + 1}: {len(batch)} links")
            
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
                
                # Call API
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Accept": "application/json"
                }
                
                payload = {
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": self.system_prompt},
                        {"role": "user", "content": batch_message}
                    ],
                    "max_tokens": 2048,  # Increased for batch responses
                    "temperature": 0.20,
                    "top_p": 0.70,
                    "stream": False
                }
                
                response = requests.post(
                    self.invoke_url,
                    headers=headers,
                    json=payload,
                    timeout=60  # Increased timeout for batch
                )
                response.raise_for_status()
                
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
                
                # Add URLs to results and log each classification
                for idx, (link_info, result) in enumerate(zip(batch, batch_results), 1):
                    result['url'] = link_info['url']
                    all_results.append(result)
                    
                    # Log individual result from batch
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
                for link_info in batch:
                    all_results.append({
                        'url': link_info['url'],
                        'is_back_link': False,
                        'is_course_page': False,
                        'is_course_relevant': False,
                        'confidence': 0.0,
                        'reasoning': f'Batch error: {str(e)}',
                        'error': True
                    })
        
        return all_results
    
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
                    use_heuristics: bool = True, batch_size: int = 10) -> Dict[str, List[Dict]]:
        """
        Filter links into categories: back_links, course_pages, course_relevant, and irrelevant.
        Uses batch processing for efficient AI classification.
        
        Args:
            links: List of link dictionaries
            context_url: The page where links were found
            use_heuristics: Use quick heuristics before AI classification
            batch_size: Number of links to process per AI request
        
        Returns:
            Dictionary with categorized links
        """
        back_links = []
        course_pages = []
        course_relevant = []
        irrelevant = []
        
        # Separate links that can be filtered by heuristics
        needs_ai_classification = []
        
        for link_info in links:
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
                'total': len(links),
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
