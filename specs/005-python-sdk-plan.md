# Reddit Research MCP Python SDK - Design Plan

## Executive Summary

This document outlines a plan for building a Python SDK that provides a high-level, Pythonic interface for integrating AI agents with the Reddit Research MCP server. The SDK will lower the barrier to entry for developers building AI-powered applications that need Reddit research capabilities.

## Problem Statement

Currently, consumers of the Reddit Research MCP server need to:
1. Understand the MCP protocol and its three-layer architecture (discover → schema → execute)
2. Manually handle OAuth authentication with Descope
3. Parse untyped dictionary responses
4. Implement their own error handling and retry logic

This creates friction for developers who want to focus on building their AI applications rather than learning MCP internals.

## Target Audience

- Developers building AI-powered chat applications
- Teams integrating Reddit research into existing AI agents
- Developers using frameworks like LangChain, LlamaIndex, or custom LLM orchestration

## Design Principles

Based on SDK design best practices research:

1. **Pythonic API**: Follow `import lib ... lib.method()` pattern, not `from lib import LibMethod`
2. **Flat Structure**: Avoid deep nesting; expose clean top-level API
3. **Typed Responses**: Use dataclasses/Pydantic for all return types
4. **Sensible Defaults**: Make the easy things easy, hard things possible
5. **Custom Exceptions**: Provide meaningful error types
6. **State via Classes**: Avoid global state; use `Client` class for connection state
7. **Keyword Arguments**: Use kwargs for flexibility and backwards compatibility

---

## Architecture Overview

```
reddit_research_sdk/
├── __init__.py              # Public API exports
├── client.py                # Main RedditResearchClient class
├── models/
│   ├── __init__.py
│   ├── subreddits.py        # Subreddit discovery models
│   ├── posts.py             # Post and comment models
│   └── feeds.py             # Feed management models
├── exceptions.py            # Custom exception hierarchy
├── auth.py                  # Authentication helpers
└── _internal/
    ├── __init__.py
    ├── mcp_client.py        # FastMCP client wrapper
    └── transport.py         # HTTP/SSE transport configuration
```

---

## Core Components

### 1. Client Class (`client.py`)

The main entry point for all SDK operations.

```python
from reddit_research_sdk import RedditResearchClient

# Simple initialization
client = RedditResearchClient(
    server_url="https://your-mcp-server.com",
    # Auth options (choose one):
    auth="oauth",  # Interactive OAuth flow
    # OR
    token="your-session-token",  # Pre-obtained token
)

# Async context manager usage
async with client:
    # All operations are typed and documented
    subreddits = await client.discover_subreddits("machine learning")
    posts = await client.fetch_posts("MachineLearning", limit=10)
```

#### Key Features:
- Async context manager for connection lifecycle
- Automatic authentication handling
- Connection pooling and reuse
- Progress callbacks for long operations
- Configurable timeouts and retries

### 2. Data Models (`models/`)

Typed dataclasses for all API responses:

```python
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

@dataclass
class DiscoveredSubreddit:
    """A subreddit discovered via semantic search."""
    name: str
    description: str
    subscribers: int
    confidence_score: float
    match_tier: str  # "exact", "semantic", "adjacent", "peripheral"

@dataclass
class DiscoveryResult:
    """Result from discover_subreddits operation."""
    subreddits: List[DiscoveredSubreddit]
    confidence_stats: ConfidenceStats
    tier_distribution: dict[str, int]
    query: str

@dataclass
class RedditPost:
    """A Reddit post/submission."""
    id: str
    title: str
    author: str
    subreddit: str
    score: int
    created_at: datetime
    url: str
    num_comments: int
    selftext: Optional[str] = None
    upvote_ratio: Optional[float] = None
    permalink: Optional[str] = None

@dataclass
class Comment:
    """A Reddit comment with threading support."""
    id: str
    body: str
    author: str
    score: int
    created_at: datetime
    depth: int
    replies: List['Comment'] = None

@dataclass
class Feed:
    """A saved research feed."""
    id: str
    name: str
    user_id: str
    website_url: Optional[str]
    analysis: Optional[FeedAnalysis]
    subreddits: List[SubredditOption]
    created_at: datetime
    updated_at: datetime
```

### 3. Exception Hierarchy (`exceptions.py`)

```python
class RedditResearchError(Exception):
    """Base exception for all SDK errors."""

class AuthenticationError(RedditResearchError):
    """Authentication failed or token expired."""

class ConnectionError(RedditResearchError):
    """Network or server connection error."""

class RateLimitError(RedditResearchError):
    """API rate limit exceeded."""
    retry_after: Optional[float] = None

class OperationError(RedditResearchError):
    """MCP operation failed."""
    operation_id: str
    suggestion: Optional[str] = None

class SubredditNotFoundError(OperationError):
    """Specified subreddit does not exist or is private."""

class ValidationError(RedditResearchError):
    """Invalid parameters provided."""
```

### 4. Authentication (`auth.py`)

Support multiple authentication methods:

```python
# Option 1: Interactive OAuth (opens browser)
client = RedditResearchClient(server_url="...", auth="oauth")

# Option 2: Pre-obtained session token
client = RedditResearchClient(server_url="...", token="your-token")

# Option 3: Custom token provider (for token refresh)
async def token_provider() -> str:
    # Your logic to get/refresh token
    return await get_fresh_token()

client = RedditResearchClient(server_url="...", token_provider=token_provider)

# Option 4: Descope SDK integration
from reddit_research_sdk.auth import DescopeAuth

auth = DescopeAuth(
    project_id="your-project-id",
    # Automatically handles token refresh
)
client = RedditResearchClient(server_url="...", auth=auth)
```

---

## API Design

### Core Operations

#### Discovery

```python
async def discover_subreddits(
    self,
    query: str | List[str],
    *,
    limit: int = 10,
    include_nsfw: bool = False,
    min_confidence: float = 0.0,
    progress_callback: Optional[Callable[[float], None]] = None,
) -> DiscoveryResult | dict[str, DiscoveryResult]:
    """
    Find relevant subreddits using semantic search.

    Args:
        query: Single topic or list of topics for batch discovery
        limit: Maximum subreddits to return per query (1-50)
        include_nsfw: Include NSFW communities
        min_confidence: Minimum confidence score threshold (0.0-1.0)
        progress_callback: Called with progress updates (0.0-1.0)

    Returns:
        DiscoveryResult for single query, or dict mapping queries to results

    Raises:
        ValidationError: Invalid parameters
        ConnectionError: Server unreachable

    Example:
        >>> result = await client.discover_subreddits("machine learning")
        >>> for sub in result.subreddits[:5]:
        ...     print(f"{sub.name}: {sub.confidence_score:.2f}")
        MachineLearning: 0.92
        deeplearning: 0.87
        artificial: 0.78
    """
```

#### Search

```python
async def search_subreddit(
    self,
    subreddit: str,
    query: str,
    *,
    sort: Literal["relevance", "hot", "top", "new"] = "relevance",
    time_filter: Literal["all", "year", "month", "week", "day"] = "all",
    limit: int = 10,
) -> SearchResult:
    """
    Search for posts within a specific subreddit.

    Args:
        subreddit: Subreddit name (without r/ prefix)
        query: Search terms
        sort: How to sort results
        time_filter: Time period for results
        limit: Maximum results (1-100)

    Returns:
        SearchResult with posts and metadata

    Raises:
        SubredditNotFoundError: Subreddit doesn't exist or is private
    """
```

#### Fetch Posts

```python
async def fetch_posts(
    self,
    subreddit: str,
    *,
    listing_type: Literal["hot", "new", "top", "rising"] = "hot",
    time_filter: Optional[Literal["all", "year", "month", "week", "day"]] = None,
    limit: int = 10,
) -> SubredditPostsResult:
    """
    Get posts from a single subreddit.
    """

async def fetch_multiple(
    self,
    subreddits: List[str],
    *,
    listing_type: Literal["hot", "new", "top", "rising"] = "hot",
    time_filter: Optional[Literal["all", "year", "month", "week", "day"]] = None,
    limit_per_subreddit: int = 5,
) -> dict[str, SubredditPostsResult]:
    """
    Batch fetch from multiple subreddits (70% more efficient than individual calls).
    """
```

#### Comments

```python
async def fetch_comments(
    self,
    post: str | RedditPost,  # Post ID or Post object
    *,
    comment_limit: int = 100,
    sort: Literal["best", "top", "new"] = "best",
) -> SubmissionWithComments:
    """
    Get complete comment tree for a post.

    Args:
        post: Either a post ID string or a RedditPost object
        comment_limit: Maximum comments to fetch (recommend 50-100)
        sort: How to sort comments
    """
```

#### Feed Management

```python
async def create_feed(
    self,
    name: str,
    subreddits: List[SubredditOption],
    *,
    website_url: Optional[str] = None,
    analysis: Optional[FeedAnalysis] = None,
) -> Feed:
    """Create a new saved feed."""

async def list_feeds(
    self,
    *,
    limit: int = 50,
    offset: int = 0,
) -> FeedListResult:
    """List all feeds for the authenticated user."""

async def get_feed(self, feed_id: str) -> Feed:
    """Get a specific feed by ID."""

async def update_feed(
    self,
    feed_id: str,
    *,
    name: Optional[str] = None,
    subreddits: Optional[List[SubredditOption]] = None,
    # ... other optional fields
) -> Feed:
    """Update an existing feed (partial update)."""

async def delete_feed(self, feed_id: str) -> bool:
    """Delete a feed. Returns True on success."""
```

---

## Advanced Features

### 1. Convenience Methods

High-level methods that combine multiple operations:

```python
async def research_topic(
    self,
    topic: str,
    *,
    depth: Literal["shallow", "medium", "deep"] = "medium",
    include_comments: bool = True,
) -> ResearchResult:
    """
    Comprehensive research workflow in one call.

    1. Discovers relevant subreddits
    2. Fetches top posts from each
    3. Optionally fetches comments from high-engagement posts

    Returns aggregated results with citations.
    """
```

### 2. Streaming Support

For long-running operations:

```python
async for progress in client.discover_subreddits_stream("AI"):
    if isinstance(progress, ProgressUpdate):
        print(f"Progress: {progress.percent:.0%}")
    else:
        # Final result
        result = progress
```

### 3. LangChain Integration (Future)

```python
from reddit_research_sdk.integrations.langchain import RedditResearchTool

# Use as a LangChain tool
tool = RedditResearchTool(client)
agent = create_react_agent(llm, [tool])
```

### 4. Caching Support

```python
from reddit_research_sdk import RedditResearchClient, DiskCache

client = RedditResearchClient(
    server_url="...",
    cache=DiskCache("~/.reddit_research_cache"),
    cache_ttl=3600,  # 1 hour
)
```

---

## Implementation Phases

### Phase 1: Core SDK (MVP)

**Scope:**
- `RedditResearchClient` class with basic auth (token-based)
- All core operations: discover, search, fetch_posts, fetch_multiple, fetch_comments
- Typed data models for all responses
- Custom exception hierarchy
- Basic error handling

**Deliverables:**
- PyPI package: `reddit-research-sdk`
- Documentation: README with quickstart
- Tests: Unit tests with mocked responses

### Phase 2: Authentication & Polish

**Scope:**
- OAuth flow support (interactive browser)
- Token refresh handling
- Descope SDK integration
- Progress callbacks
- Retry logic with exponential backoff
- Connection pooling

**Deliverables:**
- Auth module with multiple strategies
- Enhanced error messages
- Integration tests

### Phase 3: Feed Management & Advanced Features

**Scope:**
- Feed CRUD operations
- Convenience methods (`research_topic`)
- Streaming support
- Caching layer

**Deliverables:**
- Complete API coverage
- Performance optimizations
- Comprehensive documentation

### Phase 4: Integrations & Ecosystem

**Scope:**
- LangChain tool wrapper
- LlamaIndex integration
- OpenAI function calling format
- CLI tool for testing

**Deliverables:**
- Integration packages
- Example notebooks
- Tutorial videos

---

## Package Distribution

### PyPI Package Name
`reddit-research-sdk`

### Import Name
`reddit_research_sdk`

### Dependencies

**Required:**
- `httpx>=0.24.0` - Async HTTP client
- `pydantic>=2.0` - Data validation (or dataclasses)
- `fastmcp>=2.0.0` - MCP protocol handling

**Optional:**
- `keyring` - Secure token storage
- `rich` - Progress display in CLI

### Python Version
- Minimum: Python 3.10
- Target: Python 3.11+

---

## Usage Examples

### Basic Usage

```python
from reddit_research_sdk import RedditResearchClient

async def main():
    async with RedditResearchClient(
        server_url="https://your-server.com",
        token="your-auth-token"
    ) as client:
        # Discover relevant communities
        discovery = await client.discover_subreddits("home automation")

        print(f"Found {len(discovery.subreddits)} communities")
        for sub in discovery.subreddits[:3]:
            print(f"  r/{sub.name} - {sub.confidence_score:.0%} confidence")

        # Fetch posts from top communities
        top_subreddits = [s.name for s in discovery.subreddits[:5]]
        posts = await client.fetch_multiple(
            top_subreddits,
            listing_type="top",
            time_filter="month",
            limit_per_subreddit=10
        )

        # Analyze high-engagement posts
        for subreddit, result in posts.items():
            high_engagement = [p for p in result.posts if p.num_comments > 20]
            for post in high_engagement[:2]:
                comments = await client.fetch_comments(post, comment_limit=50)
                print(f"\n{post.title}")
                print(f"  {len(comments.comments)} top comments analyzed")
```

### With Progress Tracking

```python
from rich.progress import Progress

async with RedditResearchClient(server_url="...", token="...") as client:
    with Progress() as progress:
        task = progress.add_task("Discovering subreddits...", total=100)

        def on_progress(pct: float):
            progress.update(task, completed=pct * 100)

        result = await client.discover_subreddits(
            ["AI", "machine learning", "data science"],
            progress_callback=on_progress
        )
```

### Error Handling

```python
from reddit_research_sdk import RedditResearchClient
from reddit_research_sdk.exceptions import (
    SubredditNotFoundError,
    RateLimitError,
    AuthenticationError,
)

async with RedditResearchClient(...) as client:
    try:
        posts = await client.fetch_posts("nonexistent_subreddit_xyz")
    except SubredditNotFoundError as e:
        print(f"Subreddit not found: {e}")
    except RateLimitError as e:
        print(f"Rate limited. Retry after {e.retry_after}s")
    except AuthenticationError:
        print("Token expired, please re-authenticate")
```

---

## Open Questions

1. **Sync vs Async API**: Should we provide both? FastMCP is async-only.
   - Recommendation: Async-only for MVP, add sync wrappers in Phase 2

2. **Pydantic vs Dataclasses**: Which for data models?
   - Recommendation: Pydantic for validation, JSON serialization

3. **Relationship to FastMCP Client**: Extend or wrap?
   - Recommendation: Wrap - compose FastMCP Client internally

4. **Token Storage**: How to handle persistent tokens?
   - Recommendation: Optional `keyring` integration, default in-memory

5. **Package Scope**: Include LLM-specific integrations in core?
   - Recommendation: Separate optional packages (e.g., `reddit-research-sdk[langchain]`)

---

## Success Metrics

- **Adoption**: PyPI downloads per month
- **Developer Experience**: Time to first successful API call < 5 minutes
- **Documentation Quality**: All public APIs documented with examples
- **Test Coverage**: >90% for core functionality
- **Error Messages**: Actionable messages that help developers fix issues

---

## Next Steps

1. Review and approve this plan
2. Set up package scaffolding
3. Implement Phase 1 (Core SDK)
4. Publish alpha to PyPI
5. Gather feedback and iterate
