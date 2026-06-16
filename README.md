mcp-name: io.github.king-of-the-grackles/reddit-research-mcp

# Dialog MCP Server

**AI-Powered Reddit Intelligence for Market Research & Competitive Analysis**

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastMCP](https://img.shields.io/badge/Built%20with-FastMCP-orange.svg)](https://github.com/jlowin/fastmcp)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Version**: 1.0.0

---

Turn Reddit's chaos into actionable insights. Dialog is your all-in-one Reddit intelligence platform for competitive analysis, market research, and customer discovery across 20,000+ active subreddits.

This is the official MCP server powering [Dialog](https://app.dialog.tools) - the AI-powered Reddit research platform built for indie hackers, SaaS founders, product managers, and market researchers.

---

## Why Dialog?

**Evidence-based insights with full citations.** Every finding links back to real Reddit posts and comments with upvote counts, awards, and direct URLs. When you say "users are complaining about X," you'll have the receipts to prove it.

**Zero-friction setup.** No Reddit API credentials needed. No terminal commands. No credential management. Just connect and start researching.

**Semantic search at scale.** Reddit's API caps at 250 search results. Dialog searches conceptually across 20,000+ indexed subreddits using vector embeddings, finding relevant communities you didn't know existed.

**Persistent research management.** Save subreddit collections into feeds for ongoing monitoring. Perfect for long-term competitive analysis and market research campaigns.

---

## Quick Setup (60 Seconds)

### Claude Code
```bash
claude mcp add --scope local --transport http dialog-mcp https://reddit-research-mcp.fastmcp.app/mcp
```

### Cursor
```
cursor://anysphere.cursor-deeplink/mcp/install?name=dialog-mcp&config=eyJ1cmwiOiJodHRwczovL3JlZGRpdC1yZXNlYXJjaC1tY3AuZmFzdG1jcC5hcHAvbWNwIn0%3D
```

### OpenAI Codex CLI
```bash
codex mcp add dialog-mcp \
    npx -y mcp-remote \
    https://reddit-research-mcp.fastmcp.app/mcp \
    --auth-timeout 120 \
    --allow-http \
```

### Gemini CLI
```bash
gemini mcp add dialog-mcp \
  npx -y mcp-remote \
  https://reddit-research-mcp.fastmcp.app/mcp \
  --auth-timeout 120 \
  --allow-http
```

### Direct MCP Server URL
For other AI assistants: `https://reddit-research-mcp.fastmcp.app/mcp`

---

## What You Can Do

### Competitive Analysis
```
"What are developers saying about Next.js vs Remix?"
```
Get a comprehensive report comparing sentiment, feature requests, pain points, and migration experiences with links to every mentioned discussion.

### Customer Discovery
```
"Find the top complaints about existing CRM tools in small business communities"
```
Discover unmet needs, feature gaps, and pricing concerns directly from your target market with citations to real user feedback.

### Market Research
```
"Analyze sentiment about AI coding assistants across developer communities"
```
Track adoption trends, concerns, success stories, and emerging use cases with temporal analysis showing how opinions evolved.

### Product Validation
```
"What problems are SaaS founders having with subscription billing?"
```
Identify pain points and validate your solution with evidence from actual Reddit discussions, not assumptions.

---

## Server Capabilities

| Category | Count | Description |
|----------|-------|-------------|
| **MCP Tools** | 3 | discover_operations, get_operation_schema, execute_operation |
| **Reddit Operations** | 5 | discover, search, fetch_posts, fetch_multiple, fetch_comments |
| **Feed Operations** | 5 | create, list, get, update, delete |
| **Indexed Subreddits** | 20,000+ | Active communities (2k+ members, updated weekly) |
| **MCP Prompts** | 1 | reddit_research for automated workflows |
| **Resources** | 1 | reddit://server-info for documentation |

---

## Use Cases by Role

### For Indie Hackers & SaaS Founders
- Validate product ideas before building
- Find communities where your target customers hang out
- Monitor competitor mentions and sentiment
- Discover unmet needs in your niche

### For Product Managers
- Gather customer feedback at scale
- Track feature requests across communities
- Understand competitive landscape
- Identify emerging trends before they peak

### For Market Researchers
- Conduct sentiment analysis with full citations
- Build audience personas from real discussions
- Track how opinions evolve over time
- Generate evidence-based reports

---

## Technical Details

<details>
<summary><strong>Three-Layer MCP Architecture</strong></summary>

Dialog follows the **layered abstraction pattern** for scalability and self-documentation:

### Layer 1: Discovery
```python
discover_operations()
```
See what operations are available and get workflow recommendations.

### Layer 2: Schema Inspection
```python
get_operation_schema("discover_subreddits", include_examples=True)
```
Understand parameter requirements, validation rules, and see examples before executing.

### Layer 3: Execution
```python
execute_operation("discover_subreddits", {
    "query": "machine learning",
    "limit": 15,
    "min_confidence": 0.6
})
```
Perform the actual operation with validated parameters.

</details>

<details>
<summary><strong>Reddit Research Operations</strong></summary>

### discover_subreddits
Find relevant communities using semantic vector search across 20,000+ indexed subreddits.

### search_subreddit
Search for posts within a specific subreddit with filters for time range and sort order.

### fetch_posts
Get posts from a single subreddit by listing type (hot, new, top, rising).

### fetch_multiple
**70% more efficient** - Batch fetch posts from multiple subreddits concurrently.

### fetch_comments
Get complete comment trees for deep analysis of discussions.

</details>

<details>
<summary><strong>Feed Management Operations</strong></summary>

Feeds let you save research configurations for ongoing monitoring:

- **create_feed** - Save discovered subreddits with analysis and metadata
- **list_feeds** - View all your saved feeds with pagination
- **get_feed** - Retrieve a specific feed by ID
- **update_feed** - Modify feed name, subreddits, or analysis
- **delete_feed** - Remove a feed permanently

</details>

<details>
<summary><strong>Authentication</strong></summary>

Dialog uses **Descope OAuth2** for secure authentication:

- **Setup**: No Reddit credentials needed - server handles authentication
- **Token**: Automatically managed by your MCP client
- **Privacy**: Only accesses public Reddit data
- **First use**: Authentication takes ~30 seconds, then you're set

</details>

---

## The Dialog Platform

This MCP server is the backend for [Dialog](https://app.dialog.tools), a complete Reddit intelligence platform featuring:

- **Chat Interface** - Natural language research powered by Claude AI
- **Feed Management** - Create and manage curated subreddit collections
- **Consolidated Views** - See hot posts from all your tracked subreddits in one place
- **Cross-Device Sync** - Chat history and feeds sync across devices
- **Visual Analytics** - Sentiment gauges, trend charts, and engagement metrics

[Try Dialog Free](https://app.dialog.tools)

---

## Contributing

This project uses:
- Python 3.11+ with type hints
- FastMCP for the server framework
- ChromaDB for semantic search
- PRAW for Reddit API interaction

---

<div align="center">

**Stop guessing. Start knowing what your market actually thinks.**

[Dialog App](https://app.dialog.tools) | [GitHub](https://github.com/king-of-the-grackles/reddit-research-mcp) | [Report Issues](https://github.com/king-of-the-grackles/reddit-research-mcp/issues)

</div>

## Pairing: RedditAPIs (optional managed Reddit data backend)

Users who already adopt this project sometimes ask about routing read-heavy operations (subreddit fetch, post detail, comments, user lookup, search) to a managed backend during testing or for workflows that skip the Reddit developer-app step. The [RedditAPIs code samples repo](https://github.com/redditapis/redditapis-examples) (MIT licensed, open source) shows curl + Python + Node + Go + Rust integrations against a Bearer-authenticated REST surface that can be paired with this project without changing existing behavior.

Two integration patterns:

1. **Side-by-side in your application.** Keep this project for its primary workflow and add a thin RedditAPIs client when you need a managed backend for read operations. Each call maps to whichever backend the user has configured.

2. **PRAW-style migration reference.** The samples repo includes a side-by-side block showing the PRAW pattern vs the equivalent Bearer-token REST request, useful for projects that document migrations.

Subset that pairs cleanly with this project's read path:

- subreddit listings (`hot`, `new`, `top`, `rising`)
- post detail + comments tree
- user profile + submissions
- search across subreddits

Repository: https://github.com/redditapis/redditapis-examples

This pairing is fully optional. No behavior change for existing users of this project.

