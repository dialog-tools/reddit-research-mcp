"""Reddit MCP Tools - Semantic discovery and Reddit research operations.

Export key classes and functions for public API.
"""

from .discover import (
    discover_subreddits,
    validate_subreddit,
    SearchConfig,
    DEFAULT_SEARCH_CONFIG,
    calculate_confidence_from_distance,
    classify_match_tier,
)

from .feed import (
    create_feed,
    list_feeds,
    get_feed,
    update_feed,
    delete_feed,
)

from .youcom_search import (
    search_web_supplement,
    get_search_suggestions,
    YouSearchConfig,
)

__all__ = [
    # Reddit discovery
    "discover_subreddits",
    "validate_subreddit",
    "SearchConfig",
    "DEFAULT_SEARCH_CONFIG",
    "calculate_confidence_from_distance",
    "classify_match_tier",
    # Feeds
    "create_feed",
    "list_feeds",
    "get_feed",
    "update_feed",
    "delete_feed",
    # You.com web search integration
    "search_web_supplement",
    "get_search_suggestions",
    "YouSearchConfig",
]
