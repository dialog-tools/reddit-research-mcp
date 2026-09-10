#!/usr/bin/env python3
"""Test script for You.com integration"""

import os
import sys
import asyncio
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from tools.youcom_search import search_web_supplement, get_search_suggestions, YouSearchConfig


def test_configuration():
    """Test configuration detection"""
    print("=== Testing You.com Configuration ===")
    
    config = YouSearchConfig()
    print(f"API Key present: {bool(config.api_key)}")
    print(f"Integration enabled: {config.enabled}")
    print(f"Available: {config.is_available()}")
    print()


async def test_search_supplement():
    """Test search_web_supplement function"""
    print("=== Testing search_web_supplement ===")
    
    # Test with a simple query
    result = search_web_supplement(
        query="machine learning trends 2024",
        reddit_context="Discussion from r/MachineLearning about latest developments",
        limit=5
    )
    
    print(f"Status: {result.get('status', 'unknown')}")
    
    if result.get('status') == 'success':
        print(f"Found {len(result.get('web_results', []))} results")
        for i, res in enumerate(result.get('web_results', [])[:2], 1):
            print(f"  {i}. {res['title'][:60]}...")
    elif result.get('status') == 'unavailable':
        print("Integration not configured (this is expected without API key)")
        print(f"Message: {result.get('message')}")
    else:
        print(f"Error: {result.get('error', 'Unknown error')}")
    print()


async def test_search_suggestions():
    """Test get_search_suggestions function"""
    print("=== Testing get_search_suggestions ===")
    
    result = get_search_suggestions(
        reddit_query="python web development",
        subreddit_results=["Python", "django", "flask", "FastAPI"]
    )
    
    print(f"Status: {result.get('status', 'unknown')}")
    
    if result.get('status') == 'success':
        suggestions = result.get('suggested_searches', [])
        print(f"Generated {len(suggestions)} suggestions:")
        for i, suggestion in enumerate(suggestions, 1):
            print(f"  {i}. {suggestion}")
    elif result.get('status') == 'unavailable':
        print("Integration not configured (this is expected without API key)")
        print(f"Message: {result.get('message')}")
    else:
        print(f"Error: {result.get('error', 'Unknown error')}")
    print()


async def main():
    """Run all tests"""
    print("You.com Integration Test Suite")
    print("=" * 40)
    
    test_configuration()
    await test_search_supplement() 
    await test_search_suggestions()
    
    print("✓ All tests completed")
    
    config = YouSearchConfig()
    if not config.is_available():
        print("\nTo enable You.com integration:")
        print("1. Get API key from https://you.com/api")
        print("2. Set environment variables:")
        print("   export YDC_API_KEY=your_api_key")
        print("   export YOUCOM_SEARCH_ENABLED=true")


if __name__ == "__main__":
    asyncio.run(main())