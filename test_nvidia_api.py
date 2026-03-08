"""
Test script to debug NVIDIA API issues.
Tests basic connectivity, timeout handling, and response parsing.
"""

import os
import sys
import json
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_api_simple():
    """Test a minimal API call with short content"""
    print("\n" + "="*70)
    print("TEST 1: Simple API Test with Short Prompt")
    print("="*70)
    
    # Get API key
    api_key = os.getenv("NVIDIA_API_KEY") or os.getenv("NVIDIA_API_KEY_1")
    if not api_key:
        print("❌ ERROR: No NVIDIA_API_KEY found in environment")
        return False
    
    print(f"✓ API key found: ...{api_key[-8:]}")
    
    # Test endpoint
    endpoint = "https://integrate.api.nvidia.com/v1/chat/completions"
    print(f"✓ Using endpoint: {endpoint}")
    
    # Simple test prompt
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "meta/llama-3.3-70b-instruct",
        "messages": [
            {
                "role": "system",
                "content": "You are a helpful assistant. Respond ONLY with valid JSON."
            },
            {
                "role": "user",
                "content": 'Say "Hello World" in JSON format: {"message": "..."}'
            }
        ],
        "max_tokens": 50,
        "temperature": 0.1,
        "top_p": 0.7,
        "stream": False
    }
    
    print(f"\nSending test request...")
    print(f"  Model: {payload['model']}")
    print(f"  Max tokens: {payload['max_tokens']}")
    
    try:
        response = requests.post(endpoint, headers=headers, json=payload, timeout=30)
        print(f"\n✓ Response received (status: {response.status_code})")
        
        if response.status_code == 200:
            data = response.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            print(f"✓ API Response:\n{content}")
            return True
        else:
            print(f"❌ API Error: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except requests.Timeout:
        print("❌ Request timed out after 30 seconds")
        return False
    except Exception as e:
        print(f"❌ Request failed: {e}")
        return False


def test_api_long_content():
    """Test with longer content similar to actual usage"""
    print("\n" + "="*70)
    print("TEST 2: API Test with Longer Content")
    print("="*70)
    
    api_key = os.getenv("NVIDIA_API_KEY") or os.getenv("NVIDIA_API_KEY_1")
    if not api_key:
        print("❌ ERROR: No NVIDIA_API_KEY found")
        return False
    
    endpoint = "https://integrate.api.nvidia.com/v1/chat/completions"
    
    # Simulate a realistic extraction prompt
    long_content = """
    <html>
    <body>
    <h1>Course: AT60003 - ESDV</h1>
    <p>This is a course page with various materials.</p>
    <a href="lecture1.pdf">Lecture 1 Slides</a>
    <a href="assignment1.pdf">Assignment 1</a>
    <a href="midterm_2023.pdf">Midterm Exam 2023</a>
    """ + ("<!-- padding -->\n" * 100)  # Add some padding
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "meta/llama-3.3-70b-instruct",
        "messages": [
            {
                "role": "system",
                "content": "Extract learning materials. Respond ONLY with valid JSON."
            },
            {
                "role": "user",
                "content": f"Extract materials from this HTML:\n{long_content[:2000]}"
            }
        ],
        "max_tokens": 512,
        "temperature": 0.1,
        "top_p": 0.7,
        "stream": False
    }
    
    print(f"Sending request with ~{len(long_content)} chars of content...")
    print(f"  Max tokens: {payload['max_tokens']}")
    print(f"  Timeout: 90 seconds")
    
    try:
        response = requests.post(endpoint, headers=headers, json=payload, timeout=90)
        print(f"\n✓ Response received (status: {response.status_code})")
        
        if response.status_code == 200:
            data = response.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            print(f"✓ API Response length: {len(content)} chars")
            print(f"  Preview: {content[:200]}...")
            return True
        else:
            print(f"❌ API Error: {response.status_code}")
            print(f"Response: {response.text[:500]}")
            return False
            
    except requests.Timeout:
        print("❌ Request timed out after 90 seconds")
        print("   This suggests the model is too slow or the prompt is too large")
        return False
    except Exception as e:
        print(f"❌ Request failed: {e}")
        return False


def test_api_models():
    """Test different models to see which work best"""
    print("\n" + "="*70)
    print("TEST 3: Testing Different Models")
    print("="*70)
    
    api_key = os.getenv("NVIDIA_API_KEY") or os.getenv("NVIDIA_API_KEY_1")
    if not api_key:
        print("❌ ERROR: No NVIDIA_API_KEY found")
        return False
    
    endpoint = "https://integrate.api.nvidia.com/v1/chat/completions"
    
    # Models to test (from faster to slower)
    models = [
        "meta/llama-3.1-8b-instruct",      # Smaller, faster
        "meta/llama-3.1-70b-instruct",     # Medium
        "meta/llama-3.3-70b-instruct",     # Currently configured
    ]
    
    for model in models:
        print(f"\n--- Testing: {model} ---")
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": "Respond with valid JSON only."},
                {"role": "user", "content": 'Say {"status": "ok"}'}
            ],
            "max_tokens": 50,
            "temperature": 0.1,
            "stream": False
        }
        
        try:
            import time
            start = time.time()
            response = requests.post(endpoint, headers=headers, json=payload, timeout=60)
            elapsed = time.time() - start
            
            if response.status_code == 200:
                print(f"  ✓ Success in {elapsed:.2f}s")
            else:
                print(f"  ❌ Failed: {response.status_code}")
                
        except requests.Timeout:
            print(f"  ❌ Timed out after 60s")
        except Exception as e:
            print(f"  ❌ Error: {e}")


def main():
    """Run all tests"""
    print("\n" + "="*70)
    print("NVIDIA API DIAGNOSTICS")
    print("="*70)
    
    # Check environment
    print("\nChecking environment variables...")
    keys = ["NVIDIA_API_KEY", "NVIDIA_API_KEY_1", "NVIDIA_API_KEY_2", "NVIDIA_API_KEY_3"]
    found = []
    for key in keys:
        val = os.getenv(key)
        if val:
            found.append(f"{key}: ...{val[-8:]}")
    
    if found:
        print(f"✓ Found {len(found)} API key(s):")
        for f in found:
            print(f"  - {f}")
    else:
        print("❌ No API keys found. Please set NVIDIA_API_KEY in .env file")
        return
    
    # Run tests
    results = []
    
    results.append(("Simple API Test", test_api_simple()))
    results.append(("Long Content Test", test_api_long_content()))
    results.append(("Model Comparison", test_api_models()))
    
    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    for name, success in results:
        status = "✓ PASS" if success else "❌ FAIL"
        print(f"{status}: {name}")


if __name__ == "__main__":
    main()
