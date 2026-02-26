"""
Main entry point for the intelligent web scraper.
Orchestrates the scraping process with AI-powered link classification.
"""

import os
import sys
import logging
import argparse
from datetime import datetime
from dotenv import load_dotenv

# Add utils to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'utils'))

from utils.scraper import IntelligentScraper, MAIN_LINK
from setup.config import MAX_SCRAPING_DEPTH

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/main.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def ensure_directories():
    """Create necessary directories if they don't exist"""
    directories = ['data', 'logs']
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        logger.info(f"Ensured directory exists: {directory}")


def print_results_summary(results: dict):
    """Print a formatted summary of scraping results"""
    print("\n" + "="*60)
    print("SCRAPING RESULTS SUMMARY")
    print("="*60)
    print(f"Base URL: {results['base_url']}")
    print(f"Total Pages Visited: {results['stats']['total_visited']}")
    print(f"\nLink Classification:")
    print(f"  📄 Course Pages: {results['stats']['course_pages']}")
    print(f"  ✓ Course-Relevant Links: {results['stats']['course_relevant']}")
    print(f"  📎 File Links: {results['stats'].get('file_links', 0)}")
    print(f"  ← Back Links (filtered): {results['stats']['back_links']}")
    print(f"  ✗ Irrelevant Links: {results['stats']['irrelevant']}")
    print("\n" + "="*60)
    
    # Show some course pages (highest priority)
    if results.get('course_pages'):
        print("\nCourse Pages Found:")
        for i, link in enumerate(results['course_pages'][:5], 1):
            print(f"{i}. {link['url']}")
            if 'text' in link and link['text']:
                print(f"   Text: {link['text']}")
            if 'confidence' in link:
                print(f"   Confidence: {link['confidence']:.2f}")
        
        if len(results['course_pages']) > 5:
            print(f"   ... and {len(results['course_pages']) - 5} more course pages")
    
    # Show some course-relevant links
    if results['course_relevant_links']:
        print("\nCourse-Relevant Links (catalogs/listings):")
        for i, link in enumerate(results['course_relevant_links'][:3], 1):
            print(f"{i}. {link['url']}")
            if 'text' in link and link['text']:
                print(f"   Text: {link['text']}")
        
        if len(results['course_relevant_links']) > 3:
            print(f"   ... and {len(results['course_relevant_links']) - 3} more")
    
    # Show some file links
    if results.get('file_links'):
        print("\nFile Links Found (PDFs, images, etc.):")
        for i, link in enumerate(results['file_links'][:5], 1):
            print(f"{i}. {link['url']}")
            if 'parent_folder' in link:
                print(f"   Found in: {link['parent_folder']}")
        
        if len(results['file_links']) > 5:
            print(f"   ... and {len(results['file_links']) - 5} more files")
    
    print("\n" + "="*60 + "\n")


def main():
    """Main function to run the intelligent scraper"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Intelligent Web Scraper with AI Link Classification')
    parser.add_argument('--url', type=str, default=MAIN_LINK, 
                       help='Starting URL to scrape')
    parser.add_argument('--depth', type=int, default=MAX_SCRAPING_DEPTH, 
                       help=f'Maximum depth for recursive scraping (default: {MAX_SCRAPING_DEPTH})')
    parser.add_argument('--no-ai', action='store_true', 
                       help='Disable AI classification (extract all links)')
    parser.add_argument('--output', type=str, default='data/scraped_links.json',
                       help='Output file path for results')
    
    args = parser.parse_args()
    
    # Ensure directories exist
    ensure_directories()
    
    # Log start
    logger.info("="*60)
    logger.info("Starting Intelligent Web Scraper")
    logger.info(f"Timestamp: {datetime.now().isoformat()}")
    logger.info(f"URL: {args.url}")
    logger.info(f"Max Depth: {args.depth}")
    logger.info(f"AI Classification: {not args.no_ai}")
    logger.info("="*60)
    
    try:
        # Check for API key if AI is enabled
        if not args.no_ai:
            # Check if any API keys are available (single or multiple)
            single_key = os.getenv('NVIDIA_API_KEY')
            multiple_keys = os.getenv('NVIDIA_API_KEYS')
            numbered_keys = any(os.getenv(f'NVIDIA_API_KEY_{i}') for i in range(1, 11))
            
            if not (single_key or multiple_keys or numbered_keys):
                logger.error("No NVIDIA API keys found in environment variables!")
                logger.error("Please set at least one API key in .env file:")
                logger.error("  - NVIDIA_API_KEY=your_key")
                logger.error("  - NVIDIA_API_KEY_1=key1, NVIDIA_API_KEY_2=key2, etc.")
                logger.error("  - NVIDIA_API_KEYS=key1,key2,key3")
                logger.error("Or use --no-ai flag to disable AI classification")
                sys.exit(1)
        
        # Initialize scraper
        scraper = IntelligentScraper(
            base_url=args.url,
            use_ai_classification=not args.no_ai
        )
        
        # Run scraping
        logger.info("Starting scraping process...")
        results = scraper.scrape(max_depth=args.depth)
        
        # Save results
        output_path = scraper.save_results(output_file=args.output)
        
        # Print summary
        print_results_summary(results)
        
        # Print API key usage stats and cache stats if AI was enabled
        if not args.no_ai and scraper.classifier:
            scraper.classifier.print_api_stats()
            scraper.classifier.print_cache_stats()
            # Save cache to file
            scraper.classifier.save_cache()
        
        # Log completion
        logger.info(f"Scraping completed successfully!")
        logger.info(f"Results saved to: {output_path}")
        
        # Get unique course page and course-relevant link counts
        unique_course_pages = scraper.get_unique_course_links()
        unique_course_relevant = scraper.get_unique_course_relevant_links()
        logger.info(f"Unique course pages found: {len(unique_course_pages)}")
        logger.info(f"Unique course-relevant links found: {len(unique_course_relevant)}")
        
        return results
        
    except KeyboardInterrupt:
        logger.warning("Scraping interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error during scraping: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
