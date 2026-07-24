"""Reddit MCP Resources - Server information endpoint."""

from typing import Dict, Any
import praw


def register_resources(mcp, reddit: praw.Reddit) -> None:
    """Register server info resource with the MCP server."""
    
    @mcp.resource("reddit://server-info")
    def get_server_info() -> Dict[str, Any]:
        """
        Get comprehensive information about the Reddit MCP server's capabilities.
        
        Returns server version, available tools, prompts, and usage examples.
        """
        # Try to get rate limit info from Reddit
        rate_limit_info = {}
        try:
            # Access auth to check rate limit status
            rate_limit_info = {
                "requests_remaining": reddit.auth.limits.get('remaining', 'unknown'),
                "reset_timestamp": reddit.auth.limits.get('reset_timestamp', 'unknown'),
                "used": reddit.auth.limits.get('used', 'unknown')
            }
        except:
            rate_limit_info = {
                "status": "Rate limits tracked automatically by PRAW",
                "strategy": "Automatic retry with exponential backoff"
            }
        
        return {
            "name": "Reddit Research MCP Server",
            "version": "0.4.0",
            "description": "MCP server for comprehensive Reddit research with semantic search across 20,000+ indexed subreddits",
            "changelog": {
                "0.4.0": [
                    "Added reddit_research prompt for automated comprehensive research",
                    "Streamlined resources to focus on server-info only",
                    "Enhanced documentation for prompt-based workflows"
                ],
                "0.3.0": [
                    "Implemented three-layer architecture for clearer operation flow",
                    "Added semantic subreddit discovery with vector search",
                    "Enhanced workflow guidance with confidence-based recommendations",
                    "Improved error recovery suggestions"
                ],
                "0.2.0": [
                    "Added discover_subreddits with confidence scoring",
                    "Added fetch_multiple_subreddits for batch operations",
                    "Enhanced server-info with comprehensive documentation",
                    "Improved error handling and rate limit management"
                ],
                "0.1.0": [
                    "Initial release with search, fetch, and comment tools",
                    "Basic resources for popular subreddits and server info"
                ]
            },
            "capabilities": {
                "key_features": [
                    "Semantic search across 20,000+ indexed subreddits",
                    "Batch operations reducing API calls by 70%",
                    "Automated research workflow via prompt",
                    "Three-layer architecture for guided operations",
                    "Comprehensive citation tracking with Reddit URLs"
                ],
                "architecture": {
                    "type": "Three-Layer Architecture",
                    "workflow": [
                        "Layer 1: discover_operations() - See available operations",
                        "Layer 2: get_operation_schema(operation_id) - Get requirements",
                        "Layer 3: execute_operation(operation_id, parameters) - Execute"
                    ],
                    "description": "ALWAYS start with Layer 1, then Layer 2, then Layer 3"
                },
                "tools": [
                    {
                        "name": "discover_operations",
                        "layer": 1,
                        "description": "Discover available Reddit operations",
                        "parameters": "NONE - Call without any parameters: discover_operations() NOT discover_operations({})",
                        "purpose": "Shows all available operations and recommended workflows"
                    },
                    {
                        "name": "get_operation_schema",
                        "layer": 2,
                        "description": "Get parameter requirements for an operation",
                        "parameters": {
                            "operation_id": "The operation to get schema for (from Layer 1)",
                            "include_examples": "Whether to include examples (optional, default: true)"
                        },
                        "purpose": "Provides parameter schemas, validation rules, and examples"
                    },
                    {
                        "name": "execute_operation",
                        "layer": 3,
                        "description": "Execute a Reddit operation",
                        "parameters": {
                            "operation_id": "The operation to execute",
                            "parameters": "Parameters matching the schema from Layer 2"
                        },
                        "purpose": "Actually performs the Reddit API calls"
                    }
                ],
                "prompts": [
                    {
                        "name": "reddit_research",
                        "description": "Conduct comprehensive Reddit research on any topic or question",
                        "parameters": {
                            "research_request": "Natural language description of what to research (e.g., 'How do people feel about remote work?')"
                        },
                        "returns": "Structured workflow guiding complete research process",
                        "output": "Comprehensive markdown report with citations and metrics",
                        "usage": "Select prompt, provide research question, receive guided workflow"
                    }
                ],
                "available_operations": {
                    "discover_subreddits": "Find communities using semantic vector search (20,000+ indexed)",
                    "search_subreddit": "Search within a specific community",
                    "fetch_posts": "Get posts from one subreddit",
                    "fetch_multiple": "Batch fetch from multiple subreddits (70% more efficient)",
                    "fetch_comments": "Get complete comment tree for deep analysis"
                },
                "advanced_configuration": {
                    "description": "Fine-tune search behavior with SearchConfig for power users",
                    "searchconfig_parameters": {
                        "min_confidence": "Filter results by confidence threshold (0.0-1.0). Higher values return only highly relevant communities",
                        "EXACT_DISTANCE_THRESHOLD": "Distance threshold for 'exact' match tier (default: 0.2)",
                        "SEMANTIC_DISTANCE_THRESHOLD": "Distance threshold for 'semantic' match tier (default: 0.35)",
                        "GENERIC_PENALTY_MULTIPLIER": "Penalty applied to generic subreddits like 'funny', 'pics', 'memes' (default: 0.3)",
                        "LARGE_SUB_THRESHOLD": "Subscriber count above which to apply boost (default: 1,000,000)",
                        "LARGE_SUB_BOOST_MULTIPLIER": "Confidence boost for large subreddits (default: 1.1)",
                        "CONFIDENCE_DISTANCE_BREAKPOINTS": "Custom distance-to-confidence mapping for advanced tuning"
                    },
                    "usage": "Import SearchConfig from src.tools for programmatic customization",
                    "example": "custom_config = SearchConfig(GENERIC_PENALTY_MULTIPLIER=0.1, min_confidence=0.6)",
                    "typical_use_cases": [
                        "Stricter filtering: Increase min_confidence to 0.7+ for only highly relevant communities",
                        "Broader search: Decrease GENERIC_PENALTY_MULTIPLIER to find more generic community overlaps",
                        "Niche communities: Increase SMALL_SUB_PENALTY_MULTIPLIER to 1.0 to weight niche subs equally",
                        "Semantic tuning: Adjust CONFIDENCE_DISTANCE_BREAKPOINTS for different distance distributions"
                    ]
                },
                "resources": [
                    {
                        "uri": "reddit://server-info",
                        "description": "Comprehensive server capabilities, version, and usage information",
                        "cacheable": False,
                        "always_current": True
                    }
                ],
                "statistics": {
                    "total_tools": 3,
                    "total_prompts": 1,
                    "total_operations": 5,
                    "total_resources": 1,
                    "indexed_subreddits": "20,000+"
                }
            },
            "usage_examples": {
                "automated_research": {
                    "description": "Use the reddit_research prompt for complete automated workflow",
                    "steps": [
                        "1. Select the 'reddit_research' prompt in your MCP client",
                        "2. Provide your research question: 'What are the best practices for React development?'",
                        "3. The prompt guides the LLM through discovery, gathering, analysis, and reporting",
                        "4. Receive comprehensive markdown report with citations"
                    ]
                },
                "manual_workflow": {
                    "description": "Step-by-step manual research using the three-layer architecture",
                    "steps": [
                        "1. discover_operations() - See what's available",
                        "2. get_operation_schema('discover_subreddits') - Get requirements",
                        "3. execute_operation('discover_subreddits', {'query': 'machine learning', 'limit': 15})",
                        "4. get_operation_schema('fetch_multiple') - Get batch fetch requirements",
                        "5. execute_operation('fetch_multiple', {'subreddit_names': [...], 'limit_per_subreddit': 10})",
                        "6. get_operation_schema('fetch_comments') - Get comment requirements",
                        "7. execute_operation('fetch_comments', {'url': 'https://reddit.com/r/Python/comments/abc123/', 'comment_limit': 100})"
                    ]
                },
                "targeted_search": {
                    "description": "Find specific content in known communities",
                    "steps": [
                        "1. discover_operations()",
                        "2. get_operation_schema('search_subreddit')",
                        "3. execute_operation('search_subreddit', {'subreddit_name': 'Python', 'query': 'async', 'limit': 20})"
                    ]
                }
            },
            "performance_tips": [
                "Use the reddit_research prompt for automated comprehensive research",
                "Always follow the three-layer workflow for manual operations",
                "Use fetch_multiple for 2+ subreddits (70% fewer API calls)",
                "Single semantic search finds all relevant communities",
                "Use confidence scores to guide strategy (>0.7 = high confidence)",
                "Expect ~15-20K tokens for comprehensive research"
            ],
            "workflow_guidance": {
                "confidence_based_strategy": {
                    "high_confidence": "Scores > 0.7: Focus on top 5-8 subreddits",
                    "medium_confidence": "Scores 0.4-0.7: Cast wider net with 10-12 subreddits",
                    "low_confidence": "Scores < 0.4: Refine search terms and retry"
                },
                "research_depth": {
                    "minimum_coverage": "10+ threads, 100+ comments, 3+ subreddits",
                    "quality_thresholds": "Posts: 5+ upvotes, Comments: 2+ upvotes",
                    "author_credibility": "Prioritize 100+ karma for key insights"
                },
                "token_optimization": {
                    "discover_subreddits": "~1-2K tokens for semantic search",
                    "fetch_multiple": "~500-1000 tokens per subreddit",
                    "fetch_comments": "~2-5K tokens per post with comments",
                    "full_research": "~15-20K tokens for comprehensive analysis"
                }
            },
            "rate_limiting": {
                "handler": "PRAW automatic rate limit handling",
                "strategy": "Exponential backoff with retry",
                "current_status": rate_limit_info
            },
            "authentication": {
                "type": "Application-only OAuth",
                "scope": "Read-only access",
                "capabilities": "Search, browse, and read public content"
            },
            "support": {
                "repository": "https://github.com/king-of-the-grackles/reddit-research-mcp",
                "issues": "https://github.com/king-of-the-grackles/reddit-research-mcp/issues",
                "documentation": "See README.md and specs/ directory for architecture details"
            }
        }