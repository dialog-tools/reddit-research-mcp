from fastmcp import FastMCP, Context
from fastmcp.prompts import Message
from fastmcp.server.auth.providers.descope import DescopeProvider
from typing import Optional, Literal, List, Union, Dict, Any, Annotated

from src.auth.multi_issuer_verifier import MultiIssuerJWTVerifier
import sys
import os
import json
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from starlette.responses import Response, JSONResponse

# Load environment variables from .env file
load_dotenv()

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import get_reddit_client
from src.tools.search import search_in_subreddit
from src.tools.posts import fetch_subreddit_posts, fetch_multiple_subreddits
from src.tools.comments import fetch_submission_with_comments
from src.tools.discover import discover_subreddits
from src.tools.feed import (
    create_feed,
    list_feeds,
    get_feed,
    get_feed_config,
    update_feed,
    delete_feed,
)
from src.resources import register_resources

# Configure Descope authentication with multi-issuer support
# This allows the server to accept both:
# - OAuth/DCR tokens (issuer: https://api.descope.com/v1/apps/{project_id})
# - Session tokens (issuer: {project_id} - just the project ID per Descope docs)
project_id = os.getenv("DESCOPE_PROJECT_ID")
descope_base_url = os.getenv("DESCOPE_BASE_URL", "https://api.descope.com")
server_url = os.getenv("SERVER_URL", "http://localhost:8000")

# Create multi-issuer verifier to support both token types
multi_issuer_verifier = MultiIssuerJWTVerifier(
    issuers=[
        f"{descope_base_url}/v1/apps/{project_id}",  # OAuth DCR tokens (Claude Desktop)
        project_id,                                   # Session tokens (agent backend)
    ],
    jwks_uri=f"{descope_base_url}/{project_id}/.well-known/jwks.json",
    audience=project_id,
    algorithm="RS256",
)

auth = DescopeProvider(
    project_id=project_id,
    base_url=server_url,
    descope_base_url=descope_base_url,
    token_verifier=multi_issuer_verifier,  # Use our multi-issuer verifier
)

# Initialize MCP server with authentication
mcp = FastMCP("Reddit MCP", auth=auth, instructions="""
Reddit MCP Server - Three-Layer Architecture

🎯 ALWAYS FOLLOW THIS WORKFLOW:
1. discover_operations() - See what's available
2. get_operation_schema() - Understand requirements  
3. execute_operation() - Perform the action

📊 RESEARCH BEST PRACTICES:
• Start with discover_subreddits for ANY topic
• Use confidence scores to guide workflow:
  - High (>0.7): Direct to specific communities
  - Medium (0.4-0.7): Multi-community approach
  - Low (<0.4): Refine search terms
• Fetch comments for 10+ posts for thorough analysis
• Always include Reddit URLs when citing content

⚡ EFFICIENCY TIPS:
• Use fetch_multiple for 2+ subreddits (70% fewer API calls)
• Single vector search finds semantically related communities
• Batch operations reduce token usage

Quick Start: Read reddit://server-info for complete documentation.
""")

# Add public health check endpoint (no auth required)
@mcp.custom_route("/health", methods=["GET"])
async def health_check(request) -> Response:
    """Public health check endpoint - no authentication required.

    Allows clients to verify the server is running before attempting OAuth.
    """
    try:
        return JSONResponse({
            "status": "ok",
            "server": "Reddit MCP",
            "version": "1.0.0",
            "auth_required": True,
            "auth_endpoint": "/.well-known/oauth-authorization-server"
        })
    except Exception as e:
        print(f"ERROR: Health check failed: {e}", flush=True)
        return JSONResponse(
            {"status": "error", "message": str(e)},
            status_code=500
        )

# Add public server info endpoint (no auth required)
@mcp.custom_route("/server-info", methods=["GET"])
async def server_info(request) -> Response:
    """Public server information endpoint - no authentication required.

    Provides server metadata and capabilities to help clients understand
    what authentication and features are available.
    """
    try:
        print(f"Server info requested from {request.client.host if request.client else 'unknown'}", flush=True)
        return JSONResponse({
            "name": "Reddit MCP",
            "version": "1.0.0",
            "description": "Reddit research and analysis tools with semantic subreddit discovery",
            "authentication": {
                "required": True,
                "type": "oauth2",
                "provider": "descope",
                "authorization_server": f"{os.getenv('SERVER_URL', 'http://localhost:8000')}/.well-known/oauth-authorization-server"
            },
            "capabilities": {
                "tools": ["discover_operations", "get_operation_schema", "execute_operation"],
                "tools_count": 3,
                "supports_resources": True,
                "supports_prompts": True,
                "reddit_operations": {
                    "discover_subreddits": "Semantic search for relevant communities",
                    "search_subreddit": "Search within a specific subreddit",
                    "fetch_posts": "Get posts from a subreddit",
                    "fetch_multiple": "Batch fetch from multiple subreddits",
                    "fetch_comments": "Get complete comment trees"
                }
            }
        })
    except Exception as e:
        print(f"ERROR: Server info request failed: {e}", flush=True)
        return JSONResponse(
            {"status": "error", "message": str(e)},
            status_code=500
        )

# Add public MCP config endpoint for server discovery (no auth required)
# This follows the emerging .well-known/mcp-config standard for MCP server discovery
# Used by MCP marketplaces and clients to understand server capabilities without authentication
@mcp.custom_route("/.well-known/mcp-config", methods=["GET"])
async def mcp_config(request) -> Response:
    """Public MCP configuration endpoint - no authentication required.

    Provides server discovery information for MCP clients and marketplaces.
    This endpoint allows automated tools to scan and understand MCP server
    capabilities without needing to authenticate first.
    """
    try:
        server_base_url = os.getenv('SERVER_URL', 'http://localhost:8000')
        return JSONResponse({
            "version": "1.0",
            "servers": [
                {
                    "name": "Dialog MCP Server",
                    "description": "Reddit research and analysis tools with semantic subreddit discovery across 20,000+ indexed communities",
                    "endpoint": f"{server_base_url}/mcp",
                    "transport": "sse",
                    "capabilities": ["tools", "resources", "prompts"],
                    "authentication": {
                        "required": True,
                        "type": "oauth2",
                        "authorization_server": f"{server_base_url}/.well-known/oauth-authorization-server"
                    },
                    "tools": [
                        {
                            "name": "discover_operations",
                            "description": "Discover available Reddit operations and recommended workflows"
                        },
                        {
                            "name": "get_operation_schema",
                            "description": "Get detailed requirements and parameters for a Reddit operation"
                        },
                        {
                            "name": "execute_operation",
                            "description": "Execute a Reddit operation with validated parameters"
                        }
                    ],
                    "operations": {
                        "discover_subreddits": "Find communities using semantic vector search",
                        "search_subreddit": "Search within a specific subreddit",
                        "fetch_posts": "Get posts from a subreddit",
                        "fetch_multiple": "Batch fetch from multiple subreddits",
                        "fetch_comments": "Get complete comment trees for analysis",
                        "create_feed": "Create a new feed with analysis and subreddits",
                        "list_feeds": "List all feeds for the authenticated user",
                        "get_feed": "Get a specific feed by ID",
                        "get_feed_config": "Get feed configuration with subreddit names",
                        "update_feed": "Update an existing feed",
                        "delete_feed": "Delete a feed"
                    },
                    "prompts": [
                        {
                            "name": "reddit_research",
                            "description": "Conduct comprehensive Reddit research on any topic or question"
                        }
                    ],
                    "resources": [
                        {
                            "uri": "reddit://server-info",
                            "description": "Comprehensive server capabilities, version, and usage information"
                        }
                    ]
                }
            ]
        })
    except Exception as e:
        print(f"ERROR: MCP config request failed: {e}", flush=True)
        return JSONResponse(
            {"status": "error", "message": str(e)},
            status_code=500
        )


# RFC 9728 Protected Resource Metadata — user-registered shadow of the
# framework-provided PRM route. fastmcp.app's AWS edge currently returns 405
# for the framework-registered /.well-known/oauth-protected-resource/mcp
# without forwarding to origin; this custom route reaches origin through the
# same edge path as the working /.well-known/mcp-config above. Remove when
# FastMCP Cloud fixes the edge routing.
@mcp.custom_route("/.well-known/oauth-protected-resource/mcp", methods=["GET"])
async def oauth_protected_resource(request) -> Response:
    server_base_url = os.getenv("SERVER_URL", "http://localhost:8000").rstrip("/")
    project = os.getenv("DESCOPE_PROJECT_ID")
    descope_base = os.getenv("DESCOPE_BASE_URL", "https://api.descope.com").rstrip("/")
    return JSONResponse({
        "resource": f"{server_base_url}/mcp",
        "authorization_servers": [f"{descope_base}/v1/apps/{project}"],
        "bearer_methods_supported": ["header"],
        "scopes_supported": [],
    })


# Initialize Reddit client (will be updated with config when available)
reddit = None


def initialize_reddit_client():
    """Initialize Reddit client with environment config."""
    global reddit
    reddit = get_reddit_client()
    # Register resources with the new client
    register_resources(mcp, reddit)

# Initialize with environment variables initially
try:
    initialize_reddit_client()
except Exception as e:
    print(f"DEBUG: Reddit init failed: {e}", flush=True)


# Three-Layer Architecture Implementation

@mcp.tool(
    description="Discover available Reddit operations and recommended workflows",
    annotations={"readOnlyHint": True}
)
def discover_operations(ctx: Context) -> Dict[str, Any]:
    """
    LAYER 1: Discover what operations this MCP server provides.
    Start here to understand available capabilities.
    """
    # Phase 1: Accept context but don't use it yet
    return {
        "operations": {
            "discover_subreddits": "Find relevant communities using semantic search",
            "search_subreddit": "Search for posts within a specific community",
            "fetch_posts": "Get posts from a single subreddit",
            "fetch_multiple": "Batch fetch from multiple subreddits (70% more efficient)",
            "fetch_comments": "Get complete comment tree for deep analysis",
            "create_feed": "Create a new feed with analysis and subreddits",
            "list_feeds": "List all feeds for the authenticated user",
            "get_feed": "Get a specific feed by ID",
            "get_feed_config": "Get feed configuration with subreddit names",
            "update_feed": "Update an existing feed",
            "delete_feed": "Delete a feed"
        },
        "recommended_workflows": {
            "comprehensive_research": [
                "discover_subreddits → fetch_multiple → fetch_comments",
                "Best for: Thorough analysis across communities"
            ],
            "targeted_search": [
                "discover_subreddits → search_subreddit → fetch_comments",
                "Best for: Finding specific content in relevant communities"
            ],
            "feed_workflow": [
                "discover_subreddits → create_feed → list_feeds",
                "Best for: Saving research results for later use"
            ]
        },
        "next_step": "Use get_operation_schema() to understand requirements"
    }


@mcp.tool(
    description="Get detailed requirements and parameters for a Reddit operation",
    annotations={"readOnlyHint": True}
)
def get_operation_schema(
    operation_id: Annotated[str, "Operation ID from discover_operations"],
    include_examples: Annotated[bool, "Include example parameter values"] = True,
    ctx: Context = None
) -> Dict[str, Any]:
    """
    LAYER 2: Get parameter requirements for an operation.
    Use after discover_operations to understand how to call operations.
    """
    # Phase 1: Accept context but don't use it yet
    schemas = {
        "discover_subreddits": {
            "description": "Find communities using semantic vector search with configurable filtering and batch discovery",
            "parameters": {
                "query": {
                    "type": "string",
                    "required_one_of": ["query", "queries"],
                    "description": "Single topic to find communities for",
                    "validation": "2-100 characters"
                },
                "queries": {
                    "type": "array[string] or JSON string",
                    "required_one_of": ["query", "queries"],
                    "description": "Multiple topics for batch discovery (more efficient than individual queries)",
                    "example": '["machine learning", "deep learning", "neural networks"]',
                    "tip": "Batch mode reduces API calls and token usage by ~40%"
                },
                "limit": {
                    "type": "integer",
                    "required": False,
                    "default": 10,
                    "range": [1, 50],
                    "description": "Number of communities to return per query"
                },
                "include_nsfw": {
                    "type": "boolean",
                    "required": False,
                    "default": False,
                    "description": "Whether to include NSFW communities"
                },
                "min_confidence": {
                    "type": "float",
                    "required": False,
                    "default": 0.0,
                    "range": [0.0, 1.0],
                    "description": "Minimum confidence score threshold for results",
                    "guidance": {
                        "0.0-0.3": "Very inclusive, includes tangentially related communities",
                        "0.3-0.6": "Balanced, moderate relevance requirements",
                        "0.6-0.8": "Strict, only highly relevant communities",
                        "0.8-1.0": "Very strict, only exact semantic matches"
                    }
                }
            },
            "returns": {
                "subreddits": "Array with confidence scores (0-1) and match tiers",
                "confidence_stats": "Distribution statistics (mean, median, min, max, std_dev)",
                "tier_distribution": "Breakdown by match quality (exact, semantic, adjacent, peripheral)",
                "quality_indicators": {
                    "good": "5+ subreddits with confidence > 0.7",
                    "moderate": "3-5 subreddits with confidence 0.5-0.7",
                    "poor": "All results below 0.5 confidence - refine search terms"
                }
            },
            "notes": [
                "Supports real-time progress reporting via context",
                "Lower distances map to higher confidence scores",
                "Generic subreddits (funny, pics, memes) are penalized unless directly searched",
                "Batch mode returns results keyed by query for easy analysis"
            ],
            "examples": [] if not include_examples else [
                {"query": "machine learning", "limit": 15},
                {"query": "python web development", "limit": 10, "min_confidence": 0.6},
                {"queries": ["machine learning", "deep learning", "neural networks"], "limit": 10},
                {"queries": "[\"web framework\", \"api design\"]", "include_nsfw": False, "min_confidence": 0.5}
            ]
        },
        "search_subreddit": {
            "description": "Search for posts within a specific subreddit",
            "parameters": {
                "subreddit_name": {
                    "type": "string",
                    "required": True,
                    "description": "Exact subreddit name (without r/ prefix)",
                    "tip": "Use exact name from discover_subreddits"
                },
                "query": {
                    "type": "string",
                    "required": True,
                    "description": "Search terms"
                },
                "sort": {
                    "type": "enum",
                    "options": ["relevance", "hot", "top", "new"],
                    "default": "relevance",
                    "description": "How to sort results"
                },
                "time_filter": {
                    "type": "enum",
                    "options": ["all", "year", "month", "week", "day"],
                    "default": "all",
                    "description": "Time period for results"
                },
                "limit": {
                    "type": "integer",
                    "default": 10,
                    "range": [1, 100],
                    "description": "Maximum number of results"
                }
            },
            "examples": [] if not include_examples else [
                {"subreddit_name": "MachineLearning", "query": "transformers", "limit": 20},
                {"subreddit_name": "Python", "query": "async", "sort": "top", "time_filter": "month"}
            ]
        },
        "fetch_posts": {
            "description": "Get posts from a single subreddit",
            "parameters": {
                "subreddit_name": {
                    "type": "string",
                    "required": True,
                    "description": "Exact subreddit name (without r/ prefix)"
                },
                "listing_type": {
                    "type": "enum",
                    "options": ["hot", "new", "top", "rising"],
                    "default": "hot",
                    "description": "Type of posts to fetch"
                },
                "time_filter": {
                    "type": "enum",
                    "options": ["all", "year", "month", "week", "day"],
                    "default": None,
                    "description": "Time period (only for 'top' listing)"
                },
                "limit": {
                    "type": "integer",
                    "default": 10,
                    "range": [1, 100],
                    "description": "Number of posts to fetch"
                }
            },
            "examples": [] if not include_examples else [
                {"subreddit_name": "technology", "listing_type": "hot", "limit": 15},
                {"subreddit_name": "science", "listing_type": "top", "time_filter": "week", "limit": 20}
            ]
        },
        "fetch_multiple": {
            "description": "Batch fetch from multiple subreddits efficiently",
            "parameters": {
                "subreddit_names": {
                    "type": "array[string]",
                    "required": True,
                    "max_items": 10,
                    "description": "List of subreddit names (without r/ prefix)",
                    "tip": "Use names from discover_subreddits"
                },
                "listing_type": {
                    "type": "enum",
                    "options": ["hot", "new", "top", "rising"],
                    "default": "hot",
                    "description": "Type of posts to fetch"
                },
                "time_filter": {
                    "type": "enum",
                    "options": ["all", "year", "month", "week", "day"],
                    "default": None,
                    "description": "Time period (only for 'top' listing)"
                },
                "limit_per_subreddit": {
                    "type": "integer",
                    "default": 5,
                    "range": [1, 25],
                    "description": "Posts per subreddit"
                }
            },
            "efficiency": {
                "vs_individual": "70% fewer API calls",
                "token_usage": "~500-1000 tokens per subreddit"
            },
            "examples": [] if not include_examples else [
                {"subreddit_names": ["Python", "django", "flask"], "listing_type": "hot", "limit_per_subreddit": 5},
                {"subreddit_names": ["MachineLearning", "deeplearning"], "listing_type": "top", "time_filter": "week", "limit_per_subreddit": 10}
            ]
        },
        "fetch_comments": {
            "description": "Get complete comment tree for a post",
            "parameters": {
                "submission_id": {
                    "type": "string",
                    "required_one_of": ["submission_id", "url"],
                    "description": "Reddit post ID (e.g., '1abc234')"
                },
                "url": {
                    "type": "string",
                    "required_one_of": ["submission_id", "url"],
                    "description": "Full Reddit URL to the post"
                },
                "comment_limit": {
                    "type": "integer",
                    "default": 100,
                    "recommendation": "50-100 for analysis",
                    "description": "Maximum comments to fetch"
                },
                "comment_sort": {
                    "type": "enum",
                    "options": ["best", "top", "new"],
                    "default": "best",
                    "description": "How to sort comments"
                }
            },
            "examples": [] if not include_examples else [
                {"submission_id": "1abc234", "comment_limit": 100},
                {"url": "https://reddit.com/r/Python/comments/xyz789/", "comment_limit": 50, "comment_sort": "top"}
            ]
        },
        "create_feed": {
            "description": "Create a new feed with analysis and selected subreddits",
            "parameters": {
                "name": {
                    "type": "string",
                    "required": True,
                    "description": "Name for the feed (1-255 chars)"
                },
                "website_url": {
                    "type": "string",
                    "required": False,
                    "description": "URL of the website being analyzed (optional)"
                },
                "analysis": {
                    "type": "object",
                    "required": False,
                    "description": "Feed analysis data (optional)",
                    "properties": {
                        "description": "Description of topic/product/interest (10-1000 chars)",
                        "audience_personas": "Array of persona tags (1-10 items)",
                        "keywords": "Array of relevant keywords (1-50 items)"
                    }
                },
                "selected_subreddits": {
                    "type": "array[object]",
                    "required": True,
                    "min_items": 1,
                    "max_items": 50,
                    "description": "List of selected subreddits",
                    "item_properties": {
                        "name": "Subreddit name (1-100 chars)",
                        "description": "Subreddit description (max 1000 chars)",
                        "subscribers": "Number of subscribers (integer >= 0)",
                        "confidence_score": "Relevance score (0.0-1.0)"
                    }
                }
            },
            "examples": [] if not include_examples else [
                {
                    "name": "AI Research Feed",
                    "website_url": "https://example.com",
                    "analysis": {
                        "description": "AI-powered data analysis platform for businesses",
                        "audience_personas": ["data scientists", "business analysts", "ML engineers"],
                        "keywords": ["machine learning", "data analysis", "business intelligence"]
                    },
                    "selected_subreddits": [
                        {"name": "MachineLearning", "description": "ML community", "subscribers": 2500000, "confidence_score": 0.85},
                        {"name": "datascience", "description": "Data science discussions", "subscribers": 1200000, "confidence_score": 0.78}
                    ]
                }
            ]
        },
        "list_feeds": {
            "description": "List all feeds for the authenticated user",
            "parameters": {
                "limit": {
                    "type": "integer",
                    "required": False,
                    "default": 50,
                    "range": [1, 100],
                    "description": "Maximum number of feeds to return"
                },
                "offset": {
                    "type": "integer",
                    "required": False,
                    "default": 0,
                    "description": "Number of feeds to skip (for pagination)"
                }
            },
            "examples": [] if not include_examples else [
                {"limit": 10, "offset": 0},
                {"limit": 25, "offset": 50}
            ]
        },
        "get_feed": {
            "description": "Get a specific feed by ID",
            "parameters": {
                "feed_id": {
                    "type": "string",
                    "required": True,
                    "description": "UUID of the feed to retrieve"
                }
            },
            "examples": [] if not include_examples else [
                {"feed_id": "550e8400-e29b-41d4-a716-446655440000"}
            ]
        },
        "get_feed_config": {
            "description": "Get configuration for a feed (subreddit names, settings)",
            "parameters": {
                "feed_id": {
                    "type": "string",
                    "required": True,
                    "description": "UUID of the feed to get config for"
                }
            },
            "returns": {
                "profile_id": "UUID of the feed",
                "profile_name": "Name of the feed",
                "subreddits": "Array of subreddit names (strings)",
                "show_nsfw": "Whether NSFW content is enabled",
                "has_subreddits": "Whether feed has any subreddits configured"
            },
            "examples": [] if not include_examples else [
                {"feed_id": "550e8400-e29b-41d4-a716-446655440000"}
            ]
        },
        "update_feed": {
            "description": "Update an existing feed (partial update - only include fields to change)",
            "parameters": {
                "feed_id": {
                    "type": "string",
                    "required": True,
                    "description": "UUID of the feed to update"
                },
                "name": {
                    "type": "string",
                    "required": False,
                    "description": "New name for the feed (1-255 chars)"
                },
                "website_url": {
                    "type": "string",
                    "required": False,
                    "description": "Updated website URL"
                },
                "analysis": {
                    "type": "object",
                    "required": False,
                    "description": "Updated feed analysis data"
                },
                "selected_subreddits": {
                    "type": "array[object]",
                    "required": False,
                    "description": "Updated list of selected subreddits"
                }
            },
            "examples": [] if not include_examples else [
                {"feed_id": "550e8400-e29b-41d4-a716-446655440000", "name": "Updated Feed Name"},
                {
                    "feed_id": "550e8400-e29b-41d4-a716-446655440000",
                    "selected_subreddits": [
                        {"name": "Python", "description": "Python programming", "subscribers": 1500000, "confidence_score": 0.9}
                    ]
                }
            ]
        },
        "delete_feed": {
            "description": "Delete a feed",
            "parameters": {
                "feed_id": {
                    "type": "string",
                    "required": True,
                    "description": "UUID of the feed to delete"
                }
            },
            "examples": [] if not include_examples else [
                {"feed_id": "550e8400-e29b-41d4-a716-446655440000"}
            ]
        }
    }
    
    if operation_id not in schemas:
        return {
            "error": f"Unknown operation: {operation_id}",
            "available": list(schemas.keys()),
            "hint": "Use discover_operations() first"
        }
    
    return schemas[operation_id]


@mcp.tool(
    description="Execute a Reddit operation with validated parameters",
    annotations={"readOnlyHint": False, "openWorldHint": True}
)
async def execute_operation(
    operation_id: Annotated[str, "Operation to execute"],
    parameters: Annotated[Dict[str, Any], "Parameters matching the schema"],
    ctx: Context = None
) -> Dict[str, Any]:
    """
    LAYER 3: Execute a Reddit operation.
    Only use after getting schema from get_operation_schema.
    """
    # Phase 1: Accept context but don't use it yet

    # Normalize common parameter aliases
    param_aliases = {"subreddit": "subreddit_name"}
    for alias, canonical in param_aliases.items():
        if alias in parameters and canonical not in parameters:
            parameters[canonical] = parameters.pop(alias)

    # Operation ID aliases (map function names to operation IDs)
    operation_aliases = {
        "search_in_subreddit": "search_subreddit",
        "fetch_subreddit_posts": "fetch_posts",
        "fetch_multiple_subreddits": "fetch_multiple",
        "fetch_submission_with_comments": "fetch_comments",
    }
    operation_id = operation_aliases.get(operation_id, operation_id)

    # Operation mapping
    operations = {
        "discover_subreddits": discover_subreddits,
        "search_subreddit": search_in_subreddit,
        "fetch_posts": fetch_subreddit_posts,
        "fetch_multiple": fetch_multiple_subreddits,
        "fetch_comments": fetch_submission_with_comments,
        "create_feed": create_feed,
        "list_feeds": list_feeds,
        "get_feed": get_feed,
        "get_feed_config": get_feed_config,
        "update_feed": update_feed,
        "delete_feed": delete_feed
    }

    if operation_id not in operations:
        return {
            "success": False,
            "error": f"Unknown operation: {operation_id}",
            "available_operations": list(operations.keys())
        }

    try:
        # Add reddit client and context to params for operations that need them
        if operation_id in ["search_subreddit", "fetch_posts", "fetch_multiple", "fetch_comments"]:
            params = {**parameters, "reddit": reddit, "ctx": ctx}
        else:
            params = {**parameters, "ctx": ctx}

        # Execute operation with await for async operations
        async_operations = [
            "discover_subreddits", "fetch_multiple", "fetch_comments",
            "create_feed", "list_feeds",
            "get_feed", "get_feed_config", "update_feed", "delete_feed"
        ]
        if operation_id in async_operations:
            result = await operations[operation_id](**params)
        else:
            result = operations[operation_id](**params)

        # Check if result indicates an error (feed operations return {"error": "..."} on failure)
        if isinstance(result, dict) and "error" in result:
            return {
                "success": False,
                "error": result.get("error"),
                "suggestion": result.get("suggestion", ""),
                "data": result
            }

        return {
            "success": True,
            "data": result
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "recovery": suggest_recovery(operation_id, e)
        }


def suggest_recovery(operation_id: str, error: Exception) -> str:
    """Helper to suggest recovery actions based on error type."""
    error_str = str(error).lower()
    
    if "not found" in error_str or "404" in error_str:
        return "Verify the subreddit name or use discover_subreddits"
    elif "rate" in error_str or "429" in error_str:
        return "Rate limited - reduce limit parameter or wait before retrying"
    elif "private" in error_str or "403" in error_str:
        return "Subreddit is private - try other communities"
    elif "invalid" in error_str or "validation" in error_str:
        return "Check parameters match schema from get_operation_schema"
    else:
        return "Check parameters match schema from get_operation_schema"


# Research Workflow Prompt Template
RESEARCH_WORKFLOW_PROMPT = """
You are conducting comprehensive Reddit research based on this request: "{research_request}"

## WORKFLOW TO FOLLOW:

### PHASE 1: DISCOVERY
1. First, call discover_operations() to see available operations
2. Then call get_operation_schema("discover_subreddits") to understand the parameters
3. Extract the key topic/question from the research request and execute:
   execute_operation("discover_subreddits", {{"query": "<topic from request>", "limit": 15}})
4. Note the confidence scores for each discovered subreddit

### PHASE 2: STRATEGY SELECTION
Based on confidence scores from discovery:
- **High confidence (>0.7)**: Focus on top 5-8 most relevant subreddits
- **Medium confidence (0.4-0.7)**: Cast wider net with 10-12 subreddits  
- **Low confidence (<0.4)**: Refine search terms and retry discovery

### PHASE 3: GATHER POSTS
Use batch operation for efficiency:
execute_operation("fetch_multiple", {{
    "subreddit_names": [<list from discovery>],
    "listing_type": "top",
    "time_filter": "year",
    "limit_per_subreddit": 10
}})

### PHASE 4: DEEP DIVE INTO DISCUSSIONS
For posts with high engagement (10+ comments, 5+ upvotes):
execute_operation("fetch_comments", {{
    "submission_id": "<post_id>",
    "comment_limit": 100,
    "comment_sort": "best"
}})

Target: Analyze 100+ total comments across 10+ subreddits

### PHASE 5: SYNTHESIZE FINDINGS

Create a comprehensive report that directly addresses the research request:

# Research Report: {research_request}
*Generated: {timestamp}*

## Executive Summary
- Direct answer to the research question
- Key findings with confidence levels
- Coverage metrics: X subreddits, Y posts, Z comments analyzed

## Communities Analyzed
| Subreddit | Subscribers | Relevance Score | Posts Analyzed | Key Insights |
|-----------|------------|-----------------|----------------|--------------|
| [data]    | [count]    | [0.0-1.0]      | [count]        | [summary]    |

## Key Findings

### [Finding that directly addresses the research request]
**Community Consensus**: [Strong/Moderate/Split/Emerging]

Evidence from Reddit:
- u/[username] in r/[subreddit] stated: "exact quote" [↑450](https://reddit.com/r/subreddit/comments/abc123/)
- Discussion with 200+ comments shows... [link](url)
- Highly awarded post argues... [↑2.3k, Gold×3](url)

### [Additional relevant findings...]
[Continue with 2-4 more key findings that answer different aspects of the research request]

## Temporal Trends
- How perspectives have evolved over time
- Recent shifts in community sentiment
- Emerging viewpoints in the last 30 days

## Notable Perspectives
- Expert opinions (verified flairs, high karma users 10k+)
- Contrarian views worth considering
- Common misconceptions identified

## Data Quality Metrics
- Total subreddits analyzed: [count]
- Total posts reviewed: [count]
- Total comments analyzed: [count]  
- Unique contributors: [count]
- Date range: [oldest] to [newest]
- Average post score: [score]
- High-karma contributors (10k+): [count]

## Limitations
- Geographic/language bias (primarily English-speaking communities)
- Temporal coverage (data from [date range])
- Communities not represented in analysis

---
*Research methodology: Semantic discovery across 20,000+ indexed subreddits, followed by deep analysis of high-engagement discussions*

CRITICAL REQUIREMENTS:
- Never fabricate Reddit content - only cite actual posts/comments from the data
- Every claim must link to its Reddit source with a clickable URL
- Include upvote counts and awards for credibility assessment
- Note when content is [deleted] or [removed]
- Track temporal context (when was this posted?)
- Answer the specific research request - don't just summarize content
"""


@mcp.prompt(
    name="reddit_research",
    description="Conduct comprehensive Reddit research on any topic or question",
    tags={"research", "analysis", "comprehensive"}
)
def reddit_research(research_request: str) -> List[Message]:
    """
    Guides comprehensive Reddit research based on a natural language request.
    
    Args:
        research_request: Natural language description of what to research
                         Examples: "How do people feel about remote work?",
                                 "Best practices for Python async programming",
                                 "Community sentiment on electric vehicles"
    
    Returns:
        Structured messages guiding the LLM through the complete research workflow
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M UTC")
    
    return [
        Message(
            role="assistant", 
            content=RESEARCH_WORKFLOW_PROMPT.format(
                research_request=research_request,
                timestamp=timestamp
            )
        ),
        Message(
            role="user",
            content=f"Please conduct comprehensive Reddit research to answer: {research_request}"
        )
    ]


def main():
    """Main entry point for the server."""
    print("Reddit MCP Server starting...", flush=True)
    
    # Try to initialize the Reddit client with available configuration
    try:
        initialize_reddit_client()
        print("Reddit client initialized successfully", flush=True)
    except Exception as e:
        print(f"WARNING: Failed to initialize Reddit client: {e}", flush=True)
        print("Server will run with limited functionality.", flush=True)
        print("\nPlease provide Reddit API credentials via:", flush=True)
        print("  1. Environment variables: REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USER_AGENT", flush=True)
        print("  2. Config file: .mcp-config.json", flush=True)
    
    # Run with stdio transport
    mcp.run()


if __name__ == "__main__":
    main()