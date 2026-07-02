mcp-name: io.github.king-of-the-grackles/reddit-research-mcp

# Dialog MCP Server

**Open source Reddit intelligence, part of the research engine that powers [Dialog](https://app.dialog.tools)**

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastMCP](https://img.shields.io/badge/Built%20with-FastMCP-orange.svg)](https://github.com/jlowin/fastmcp)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Version**: 1.0.1

---

Turn Reddit's chaos into evidence-backed insights. This MCP server gives any AI assistant semantic search across 20,000+ active subreddits, deep-dive access to posts and comment threads, and saved feeds for ongoing monitoring. Every finding comes with citations to real posts and comments.

It's fully usable on its own, for free, in Claude Code, Cursor, Codex, Gemini CLI, or any MCP-compatible client. It's also part of the research engine that powers [Dialog](https://app.dialog.tools), the AI agent platform for continuous market intelligence, where it ships connected to every agent.

---

## Why This Server?

**Evidence-based insights with full citations.** Every finding links back to real Reddit posts and comments with upvote counts, awards, and direct URLs. When you say "users are complaining about X," you'll have the receipts to prove it.

**Zero-friction setup.** No Reddit API credentials needed. No terminal commands. No credential management. Just connect and start researching.

**Semantic search at scale.** Reddit's API caps at 250 search results. This server searches conceptually across 20,000+ indexed subreddits using vector embeddings, finding relevant communities you didn't know existed.

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

### Ongoing Monitoring
```
"Save these communities as a feed so we can track competitor sentiment over time"
```
Build curated feeds of the communities that matter to you, then come back to them in any session. Want this to run on a schedule and land in Slack? That's what [Dialog](https://app.dialog.tools) adds on top.

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

The server follows the **layered abstraction pattern** for scalability and self-documentation:

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

The server uses **Descope OAuth2** for secure authentication:

- **Setup**: No Reddit credentials needed - server handles authentication
- **Token**: Automatically managed by your MCP client
- **Privacy**: Only accesses public Reddit data
- **First use**: Authentication takes ~30 seconds, then you're set

</details>

---

## Want This Running on Autopilot? Meet Dialog

This server is free and fully usable standalone. [Dialog](https://app.dialog.tools) is the hosted platform where it plugs into a larger research engine: AI agents that combine this Reddit server with 45+ other integrations to run your research continuously and deliver the results where you work.

| | This MCP server (free, open source) | Dialog platform |
|---|---|---|
| **Reddit research** | Full access: semantic discovery, search, posts, comments, feeds | This same server, connected by default to every agent |
| **How it runs** | On demand, inside your AI assistant | Autonomous agents powered by Claude that plan and execute multi-step research |
| **Scheduling** | Manual, session by session | Automations that run on a schedule and land in a persistent inbox |
| **Delivery** | Your chat window | Formatted reports with inline charts in Slack, Telegram, or the web app |
| **Data sources** | Reddit | Reddit plus 45+ integrations: Gmail, Slack, Linear, HubSpot, Apollo, PostHog, Google Drive, and more |
| **Memory** | Per session | Persistent agent workspaces that build context over time |

A typical Dialog workflow: an agent monitors your competitors' communities every Monday morning, cross-references mentions against your CRM, and posts a formatted report with charts to your team's Slack channel before standup.

[Try Dialog Free](https://app.dialog.tools)

---

## Contributing

Contributions are welcome. The stack:

- Python 3.11+ with type hints
- [FastMCP](https://github.com/jlowin/fastmcp) for the server framework
- ChromaDB for semantic search
- PRAW for Reddit API interaction

### Local Development

```bash
# Clone and install (uses uv)
git clone https://github.com/king-of-the-grackles/reddit-research-mcp.git
cd reddit-research-mcp
uv sync --extra dev

# Run tests
uv run pytest

# Run the server locally
uv run reddit-mcp
```

Found a bug or have a feature idea? [Open an issue](https://github.com/king-of-the-grackles/reddit-research-mcp/issues).

---

<div align="center">

**Stop guessing. Start knowing what your market actually thinks.**

[Dialog App](https://app.dialog.tools) | [GitHub](https://github.com/king-of-the-grackles/reddit-research-mcp) | [Report Issues](https://github.com/king-of-the-grackles/reddit-research-mcp/issues)

</div>
