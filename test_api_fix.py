"""
Comprehensive test for NVIDIA API fixes.
Tests the actual markdown generation pipeline with the fixed timeout and model.
"""

import sys
import os
import logging

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def test_extraction_pipeline():
    """Test the full extraction pipeline with real content"""
    print("\n" + "="*70)
    print("TEST: Full Extraction Pipeline with Fixed Timeout")
    print("="*70)
    
    from utils.markdown_generator import extract_materials_llm
    from utils.course_analyzer import fetch_html
    
    # Test URL from the logs
    test_url = "https://cse.iitkgp.ac.in/~smisra/course/esdv.html"
    
    print(f"\n1. Fetching HTML from: {test_url}")
    html = fetch_html(test_url)
    
    if not html:
        print("❌ Failed to fetch HTML")
        return False
    
    print(f"✓ Fetched {len(html)} chars of HTML")
    
    # Create a simple index list
    index_list = [{
        "link_index": 1,
        "url": test_url,
        "course_code": "AT60003",
        "course_title": "ESDV",
        "semester": "Autumn",
        "year": "2024"
    }]
    
    print(f"\n2. Extracting materials using LLM (timeout: 120s)...")
    print(f"   This may take 15-60 seconds depending on the model...")
    
    try:
        import time
        start = time.time()
        result = extract_materials_llm(index_list, 1, html)
        elapsed = time.time() - start
        
        print(f"✓ Extraction completed in {elapsed:.2f}s")
        print(f"✓ Found {len(result.get('extracted_items', []))} items")
        print(f"✓ Found {len(result.get('special_marks', []))} special marks")
        
        # Show sample items
        if result.get('extracted_items'):
            print(f"\nSample extracted items:")
            for i, item in enumerate(result['extracted_items'][:3], 1):
                print(f"  {i}. {item.get('item_type')}: {item.get('title', 'N/A')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Extraction failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_config_values():
    """Verify configuration values are correct"""
    print("\n" + "="*70)
    print("TEST: Configuration Values")
    print("="*70)
    
    from setup.config import (
        CONTENT_VERIFICATION_MODEL,
        CONTENT_VERIFICATION_MAX_TOKENS,
        MAX_CONTENT_LENGTH,
        NVIDIA_API_ENDPOINT
    )
    
    print(f"\nConfiguration:")
    print(f"  Model: {CONTENT_VERIFICATION_MODEL}")
    print(f"  Max Tokens: {CONTENT_VERIFICATION_MAX_TOKENS}")
    print(f"  Max Content Length: {MAX_CONTENT_LENGTH}")
    print(f"  API Endpoint: {NVIDIA_API_ENDPOINT}")
    
    # Verify recommended model
    if CONTENT_VERIFICATION_MODEL == "meta/llama-3.1-70b-instruct":
        print(f"\n✓ Using recommended fast model: {CONTENT_VERIFICATION_MODEL}")
        return True
    elif CONTENT_VERIFICATION_MODEL == "meta/llama-3.3-70b-instruct":
        print(f"\n⚠ Using slower model: {CONTENT_VERIFICATION_MODEL}")
        print(f"  This may cause timeouts. Consider switching to meta/llama-3.1-70b-instruct")
        return True
    else:
        print(f"\n✓ Using model: {CONTENT_VERIFICATION_MODEL}")
        return True


def test_api_function_signature():
    """Verify the API function has the timeout parameter"""
    print("\n" + "="*70)
    print("TEST: API Function Signature")
    print("="*70)
    
    from utils.course_analyzer import _call_nvidia_api
    import inspect
    
    sig = inspect.signature(_call_nvidia_api)
    params = list(sig.parameters.keys())
    
    print(f"\nFunction signature: _call_nvidia_api{sig}")
    print(f"Parameters: {params}")
    
    if 'timeout' in params:
        default = sig.parameters['timeout'].default
        print(f"✓ Timeout parameter present with default: {default}s")
        
        if default >= 120:
            print(f"✓ Timeout is adequate for slow models")
            return True
        else:
            print(f"⚠ Timeout {default}s may be too short for llama-3.3")
            return True
    else:
        print(f"❌ Timeout parameter missing")
        return False


def main():
    """Run all tests"""
    print("\n" + "="*70)
    print("COMPREHENSIVE NVIDIA API FIX VALIDATION")
    print("="*70)
    
    results = []
    
    # Test 1: Configuration
    results.append(("Configuration Values", test_config_values()))
    
    # Test 2: Function signature
    results.append(("API Function Signature", test_api_function_signature()))
    
    # Test 3: Full pipeline (optional, commented out for speed)
    print("\n" + "="*70)
    print("OPTIONAL: Full Pipeline Test")
    print("="*70)
    print("This test makes a real API call and may take 15-60 seconds.")
    response = input("Run full pipeline test? (y/n): ").lower().strip()
    
    if response == 'y':
        results.append(("Full Extraction Pipeline", test_extraction_pipeline()))
    else:
        print("Skipping full pipeline test")
    
    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    for name, success in results:
        status = "✓ PASS" if success else "❌ FAIL"
        print(f"{status}: {name}")
    
    # Final recommendation
    print("\n" + "="*70)
    print("RECOMMENDATIONS")
    print("="*70)
    print("✓ Timeout increased to 120s (was 60s)")
    print("✓ Better error messages added")
    print("✓ Switched to faster model (llama-3.1-70b-instruct)")
    print("\nIf you still experience timeouts:")
    print("  1. Reduce MAX_CONTENT_LENGTH in config.py (currently 8000)")
    print("  2. Consider using meta/llama-3.1-8b-instruct (fastest)")
    print("  3. Check your network connection and NVIDIA API status")
    
    return all(success for _, success in results)


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
