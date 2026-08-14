# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Project Overview
This is a Reddit Research MCP (Model Context Protocol) server built with FastMCP and Python. The server enables semantic search and research across Reddit communities through a three-layer architecture.

## Development Environment

### Package Manager
This project uses `uv` as the package manager. Dependencies are managed through `pyproject.toml`.

### Common Commands

**Setup & Installation:**
```bash
# Install dependencies
uv sync

# Install in development mode
uv pip install -e .

# Create virtual environment
uv venv
```

**Running the Server:**
```bash
# Start the MCP server
uv run python src/server.py

# Alternative using npm script
npm start
```

**Testing:**
```bash
# Run all tests
uv run pytest

# Run specific test file
uv run pytest tests/test_tools.py

# Run tests with verbose output
uv run pytest -v

# Run single test
uv run pytest tests/test_context_integration.py::TestClass::test_method
```

**Development Tools:**
```bash
# Check dependencies
uv pip list

# Update dependencies
uv sync --upgrade
```

## Architecture

### Three-Layer MCP Architecture
1. **Layer 1: Discovery** - `discover_operations()` - Shows available operations
2. **Layer 2: Schema** - `get_operation_schema()` - Details operation requirements  
3. **Layer 3: Execution** - `execute_operation()` - Performs the actual work

### Core Components
- **FastMCP Server** (`src/server.py`) - Main server with Descope authentication
- **Reddit Tools** (`src/tools/`) - Modular Reddit API operations
- **Vector Search** (`src/chroma_client.py`) - Semantic subreddit discovery
- **Configuration** (`src/config.py`) - Reddit API and environment setup

### Key Tools
- `discover_subreddits` - Semantic search for relevant communities
- `search_subreddit` - Search within specific subreddit
- `fetch_posts` - Get posts from subreddit
- `fetch_multiple` - Batch fetch from multiple subreddits (70% more efficient)
- `fetch_comments` - Get complete comment trees

## Environment Configuration

### Required Environment Variables
Copy `.env.sample` to `.env` and configure:

```bash
# Reddit API (Required)
REDDIT_CLIENT_ID=your_client_id_here
REDDIT_CLIENT_SECRET=your_client_secret_here  
REDDIT_USER_AGENT=RedditMCP/1.0 by u/your_username

# Descope Authentication (Required)
DESCOPE_PROJECT_ID=P2abc...123
SERVER_URL=http://localhost:8000

# Vector Database Proxy (Optional - defaults to hosted service)
CHROMA_PROXY_URL=https://your-proxy.com
CHROMA_PROXY_API_KEY=your_api_key_here
```

## Development Guidelines

### Code Organization
- Keep tools modular in `src/tools/` directory
- Use Pydantic models for data validation (`src/models.py`)
- Follow type hints throughout (Python 3.11+)
- Use async/await patterns for all I/O operations

### Testing Strategy
- Unit tests in `tests/` directory
- Use pytest with asyncio support
- Mock external API calls in tests
- Test both successful and error scenarios

### Authentication Flow
The server uses Descope OAuth2 for authentication. Public endpoints `/health` and `/server-info` are available without auth for client verification.

### Performance Considerations
- Use `fetch_multiple` for batch operations (70% fewer API calls)
- Vector search finds semantically related communities in single query
- Batch comment fetching for deep analysis workflows

### Recommended Workflow for Research
1. Start with `discover_subreddits` for any topic
2. Use confidence scores to guide next steps:
   - High (>0.7): Direct to specific communities
   - Medium (0.4-0.7): Multi-community approach  
   - Low (<0.4): Refine search terms
3. Fetch comments from 10+ posts for thorough analysis
4. Always include Reddit URLs when citing content

## Files to Modify for Common Changes

**Adding new Reddit operations:** 
- Create new tool in `src/tools/`
- Register in `src/server.py` operations schema
- Add tests in `tests/`

**Updating authentication:**
- Modify `src/server.py` auth configuration
- Update environment variables in `.env`

**Changing vector search behavior:**
- Modify `src/chroma_client.py`
- Update discovery logic in `src/tools/discover.py`

**Adding new data models:**
- Add to `src/models.py` 
- Update relevant tools to use new models

## Specifications & Documentation
The `/specs` directory contains AI-generated architecture documents:
- `agentic-discovery-architecture.md` - Planned agent-based refactoring
- `reddit-research-agent-spec.md` - Agent implementation patterns  
- `deep-research-reddit-architecture.md` - Research workflows
- `chroma-proxy-architecture.md` - Vector search system

## MCP Client Integration

**Claude Code:**
```bash
claude mcp add --scope local --transport http reddit-research-mcp https://mcp.dialog.tools/mcp
```

**For local development:**
Update client config to point to `http://localhost:8000/mcp`