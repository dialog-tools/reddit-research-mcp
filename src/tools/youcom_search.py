"""You.com web search integration for supplementing Reddit research.

This module provides optional You.com web search functionality that complements
Reddit research by providing broader context and external validation.
"""

from typing import Optional, Dict, Any, List, Literal
import httpx
import os
import logging
from fastmcp import Context

logger = logging.getLogger(__name__)


class YouSearchConfig:
    """Configuration for You.com search integration."""
    
    def __init__(self):
        self.api_key = os.getenv("YDC_API_KEY")
        self.enabled = os.getenv("YOUCOM_SEARCH_ENABLED", "false").lower() == "true"
        self.base_url = "https://api.you.com"
        
    def is_available(self) -> bool:
        """Check if You.com search is properly configured and available."""
        return self.enabled and bool(self.api_key)


def search_web_supplement(
    query: str,
    reddit_context: Optional[str] = None,
    limit: int = 10,
    ctx: Context = None
) -> Dict[str, Any]:
    """
    Supplement Reddit research with You.com web search results.
    
    This function provides broader web context to complement Reddit discussions.
    It's designed to be optional - if You.com is not configured, it gracefully
    returns information about the missing configuration.
    
    Args:
        query: Search query to execute on the web
        reddit_context: Optional context from Reddit research to inform the search
        limit: Maximum number of results (max 20, default 10)
        ctx: FastMCP context (auto-injected by decorator)
    
    Returns:
        Dictionary containing web search results or configuration info
    """
    config = YouSearchConfig()
    
    # Check if You.com integration is available
    if not config.is_available():
        return {
            "status": "unavailable",
            "message": "You.com search integration not configured",
            "setup_instructions": {
                "api_key": "Set YDC_API_KEY environment variable with your You.com API key",
                "enable": "Set YOUCOM_SEARCH_ENABLED=true to enable the integration",
                "optional": "This feature is optional - Reddit research works without it"
            },
            "reddit_context_preserved": reddit_context,
            "query_preserved": query
        }
    
    # Validate and clean parameters
    limit = min(max(1, limit), 20)
    
    try:
        # Construct search with Reddit context if provided
        enhanced_query = query
        if reddit_context:
            enhanced_query = f"{query} (context: {reddit_context[:100]})"
        
        # Make You.com API request
        headers = {
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json",
            "X-API-Key": config.api_key
        }
        
        params = {
            "query": enhanced_query,
            "num_web_results": limit,
            "safesearch": "moderate"
        }
        
        with httpx.Client(timeout=30.0) as client:
            response = client.get(
                f"{config.base_url}/api/search",
                headers=headers,
                params=params
            )
            
            if response.status_code == 401:
                return {
                    "error": "Invalid You.com API key",
                    "status_code": 401,
                    "recovery": "Check your YDC_API_KEY environment variable"
                }
            elif response.status_code == 402:
                return {
                    "error": "You.com API quota exceeded or payment required",
                    "status_code": 402,
                    "recovery": "Check your You.com account billing status"
                }
            elif response.status_code == 429:
                return {
                    "error": "Rate limited by You.com API",
                    "status_code": 429,
                    "recovery": "Wait before retrying or reduce request frequency"
                }
            elif not response.is_success:
                return {
                    "error": f"You.com API error: HTTP {response.status_code}",
                    "status_code": response.status_code,
                    "response_body": response.text[:300] if response.text else None,
                    "recovery": "Check You.com API status or contact support"
                }
            
            data = response.json()
            
            # Parse and format results
            web_results = []
            if "web_results" in data:
                for result in data["web_results"][:limit]:
                    web_results.append({
                        "title": result.get("title", "").strip(),
                        "url": result.get("url", ""),
                        "snippet": result.get("description", "").strip(),
                        "source": "you.com"
                    })
            
            return {
                "status": "success", 
                "query": query,
                "reddit_context": reddit_context,
                "web_results": web_results,
                "total_results": len(web_results),
                "source": "You.com Web Search",
                "usage_note": "These web results supplement your Reddit research with broader context"
            }
            
    except httpx.TimeoutException:
        return {
            "error": "You.com API request timed out",
            "recovery": "Check your internet connection and retry"
        }
    except httpx.ConnectError:
        return {
            "error": "Cannot connect to You.com API",
            "recovery": "Check your internet connection and You.com API status"
        }
    except Exception as e:
        logger.error(f"Unexpected error in You.com search: {e}")
        return {
            "error": f"Unexpected error: {str(e)}",
            "recovery": "Try again or check logs for details"
        }


def get_search_suggestions(
    reddit_query: str,
    subreddit_results: Optional[List[str]] = None,
    ctx: Context = None
) -> Dict[str, Any]:
    """
    Generate web search suggestions based on Reddit research context.
    
    This helper function analyzes Reddit query patterns and suggests
    complementary web searches that might provide additional insights.
    
    Args:
        reddit_query: The original Reddit search query
        subreddit_results: Names of subreddits that were discovered/searched
        ctx: FastMCP context (auto-injected by decorator)
    
    Returns:
        Dictionary containing suggested web search queries
    """
    config = YouSearchConfig()
    
    if not config.is_available():
        return {
            "status": "unavailable",
            "message": "You.com integration not configured - suggestions not available"
        }
    
    # Generate contextual search suggestions
    suggestions = []
    
    # Base query expansion
    suggestions.append(f"{reddit_query} latest news")
    suggestions.append(f"{reddit_query} expert analysis")
    
    # Subreddit-informed suggestions
    if subreddit_results:
        community_context = " ".join(subreddit_results[:3])  # Use top 3 subreddits
        suggestions.append(f"{reddit_query} {community_context} discussion")
        suggestions.append(f"{reddit_query} beyond reddit {community_context}")
    
    # Industry/domain suggestions
    if "startup" in reddit_query.lower() or "saas" in reddit_query.lower():
        suggestions.append(f"{reddit_query} market analysis")
        suggestions.append(f"{reddit_query} industry report")
    elif "tech" in reddit_query.lower() or "software" in reddit_query.lower():
        suggestions.append(f"{reddit_query} technical documentation")
        suggestions.append(f"{reddit_query} best practices")
    
    return {
        "status": "success",
        "reddit_query": reddit_query,
        "suggested_searches": suggestions[:5],  # Limit to top 5
        "usage_note": "Use search_web_supplement with these queries for broader context"
    }