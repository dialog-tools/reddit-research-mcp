# OpenAI Apps SDK Compatibility Specification

**Status**: Planning
**Created**: November 10, 2025
**Estimated Effort**: 12-18 hours (LLM-assisted implementation)
**Timeline**: 1 week (casual pace) or 1-2 days (sprint)
**Priority**: Medium (Apps SDK is 1 month old, directory not yet open)

## Overview

This specification outlines the enhancement of the Reddit Research MCP server to be compatible with the OpenAI Apps SDK, enabling Reddit research capabilities directly within ChatGPT conversations for 800+ million users.

### What is OpenAI Apps SDK?

The OpenAI Apps SDK (launched October 6, 2025) allows developers to build applications that run directly inside ChatGPT conversations. Key characteristics:

- **Conversational Discovery**: Apps surface automatically based on conversation context
- **Custom UI**: Apps can render HTML/CSS/JavaScript widgets in chat
- **MCP Foundation**: Built on Model Context Protocol (open standard)
- **OAuth 2.1**: Secure user authentication
- **Massive Distribution**: Access to 800M+ ChatGPT users

**Current Status**: Preview/Beta (as of Nov 2025)
- Developers can build and test in Developer Mode
- App directory opens "later 2025" for public submissions
- Not available in EU/UK/Switzerland due to regulatory considerations

### Why This Matters

Our Reddit Research MCP server is already well-positioned for Apps SDK compatibility:
- ✅ Built with FastMCP (supports HTTP transport)
- ✅ OAuth already implemented (Descope provider)
- ✅ Clean three-layer architecture
- ✅ Well-structured tools and data models
- ✅ Existing React frontend with reusable components

**Opportunity**: First-mover advantage in Reddit research tools for ChatGPT platform.

---

## Current State Analysis

### What We Have (Advantages)

#### 1. **Solid MCP Server Foundation**
- **Location**: `/reddit-research-mcp/src/server.py`
- **Framework**: FastMCP with Descope OAuth
- **Transport**: stdio (for desktop AI assistants)
- **Architecture**: Three-layer (discover → schema → execute)

#### 2. **Five Core Reddit Operations**
```python
operations = {
    "discover_subreddits": discover_subreddits,      # Semantic search
    "search_subreddit": search_in_subreddit,         # Search within subreddit
    "fetch_posts": fetch_subreddit_posts,            # Get posts from subreddit
    "fetch_multiple": fetch_multiple_subreddits,     # Batch fetch (70% fewer API calls)
    "fetch_comments": fetch_submission_with_comments # Complete comment trees
}
```

#### 3. **Existing React UI Components** (Reusable!)
- **Location**: `/frontend-reddit-research-mcp/frontend/src/components/`
- **Key Components**:
  - `SubredditCard.tsx` - Displays subreddit with confidence score, subscriber count
  - `SubredditGrid.tsx` - Grid layout with select all/none controls
  - `RedditQuote.tsx` - Formatted Reddit quote with author/subreddit
  - `SentimentGauge.tsx` - Visual sentiment indicator with color-coded bar
  - `MetricBadge.tsx` - Metric display badge
- **Styling**: Tailwind CSS with custom brand colors
- **Data Types**: Already match MCP server responses (`SubredditOption`, etc.)

#### 4. **OAuth Infrastructure**
- **Provider**: Descope
- **Endpoints**: `/health`, `/server-info` (public), OAuth flows configured
- **Status**: Working for HTTP mode

### What Needs Work

#### 1. **Transport Layer** (Low Complexity - 2-4 hours)
- **Current**: stdio only
- **Needed**: HTTP with SSE support
- **Change Required**: Minimal (FastMCP supports both)

```python
# Current
mcp.run()  # defaults to stdio

# Needed
mcp.run(transport="http", host="0.0.0.0", port=8000)
```

#### 2. **Widget/Resource System** (Medium Complexity - 7-10 hours with component reuse)
- **Current**: Returns text/JSON only
- **Needed**: HTML/CSS/JavaScript widgets for visual display
- **Solution**: Convert React components to HTML templates

#### 3. **CSP Configuration** (Low Complexity - 2-3 hours)
- **Current**: None
- **Needed**: Content Security Policy for widget sandboxing
- **Domains**: Reddit thumbnails (`i.redd.it`, `external-preview.redd.it`)

#### 4. **Metadata Optimization** (Low Complexity - 2-3 hours)
- **Current**: Tool descriptions exist but not optimized
- **Needed**: "Use this when..." format for discovery
- **Testing**: Requires iteration in ChatGPT Developer Mode

#### 5. **Deployment** (Medium Complexity - 3-4 hours)
- **Current**: Local development only
- **Needed**: Cloud deployment with HTTPS
- **Platforms**: Render, Railway, or Fly.io

---

## Requirements & Architecture

### 1. HTTP Transport Configuration

**Objective**: Switch from stdio to HTTP transport for Apps SDK compatibility.

**Implementation**:
```python
# src/server.py modifications
from fastmcp import FastMCP
from starlette.middleware.cors import CORSMiddleware

mcp = FastMCP(
    "Reddit MCP",
    auth=auth,
    instructions="""..."""
)

# Add CORS for ChatGPT
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://chatgpt.com", "https://chat.openai.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if __name__ == "__main__":
    # Support both stdio (desktop) and HTTP (Apps SDK)
    import sys
    if "--http" in sys.argv:
        mcp.run(transport="http", host="0.0.0.0", port=8000)
    else:
        mcp.run()  # stdio
```

**Files to Modify**:
- `src/server.py` - Add HTTP mode support
- `package.json` - Add HTTP start script

**Effort**: 0.5-1 hour (with LLM)

---

### 2. Widget/Resource System

**Objective**: Create visual widgets for Reddit data display.

#### Widget Architecture

```
src/
├── widgets/
│   ├── __init__.py
│   ├── templates.py          # HTML templates
│   ├── subreddit_widgets.py  # Subreddit display widgets
│   ├── post_widgets.py       # Post/comment widgets
│   └── research_widgets.py   # Research report widgets
└── resources.py              # Register widgets as MCP resources
```

#### Key Widgets to Create

##### 1. Subreddit Discovery Card
**Purpose**: Display discovered subreddits with confidence scores
**Source**: Convert from `SubredditCard.tsx`
**Effort**: 1-2 hours

**Features**:
- Confidence score badge (color-coded: green >0.8, orange >0.6, gray <0.6)
- Subscriber count with formatted display (1.2M, 350K, etc.)
- Subreddit description (truncated to 2 lines)
- Hover effects

**Template Structure**:
```html
<div class="subreddit-card">
  <div class="confidence-badge confidence-{{tier}}">
    {{confidence_percent}}% match
  </div>

  <div class="subscribers">
    <svg class="icon"><!-- users icon --></svg>
    <span>{{subscribers_formatted}}</span>
  </div>

  <div class="content">
    <h3>r/{{name}}</h3>
    <p>{{description}}</p>
  </div>
</div>
```

##### 2. Subreddit Grid
**Purpose**: Display multiple subreddits in responsive grid
**Source**: Convert from `SubredditGrid.tsx`
**Effort**: 1-2 hours

**Features**:
- Responsive grid (1-3 columns based on width)
- Selection count display
- Select all/none buttons (if interactive features supported)

##### 3. Reddit Quote Block
**Purpose**: Display quoted Reddit comments with attribution
**Source**: Convert from `RedditQuote.tsx`
**Effort**: 0.5-1 hour

**Template**:
```html
<div class="reddit-quote">
  <blockquote>"{{text}}"</blockquote>
  <div class="attribution">
    <span class="author">u/{{author}}</span>
    <span>in</span>
    <a href="{{url}}" target="_blank">{{subreddit}}</a>
  </div>
</div>
```

##### 4. Sentiment Gauge
**Purpose**: Visual sentiment indicator
**Source**: Convert from `SentimentGauge.tsx`
**Effort**: 0.5-1 hour

**Features**:
- Color-coded based on sentiment (green/red/gray)
- Progress bar showing score
- Percentage display

##### 5. Post Card
**Purpose**: Display Reddit posts with metadata
**Effort**: 1-2 hours

**Features**:
- Post title and content preview
- Score, comments, subreddit
- Author and timestamp
- Link to full post

##### 6. Research Report Widget
**Purpose**: Formatted research output with sections
**Effort**: 2-3 hours

**Features**:
- Executive summary
- Community breakdown table
- Key findings sections
- Data quality metrics
- Collapsible sections

#### Widget Registration Pattern

```python
# src/widgets/__init__.py
from typing import Dict, Any
from .templates import WIDGET_STYLES

def register_widgets(mcp):
    """Register all widgets as MCP resources"""

    @mcp.resource(uri="ui://widget/subreddit_card")
    def subreddit_card_widget():
        return {
            "mimeType": "text/html+skybridge",
            "description": "Card displaying subreddit with confidence score"
        }

    @mcp.resource(uri="ui://widget/subreddit_grid")
    def subreddit_grid_widget():
        return {
            "mimeType": "text/html+skybridge",
            "description": "Grid of subreddit cards"
        }

    # ... additional widgets
```

#### Widget Rendering Pattern

```python
# src/widgets/subreddit_widgets.py
from typing import Dict, Any, List

def render_subreddit_card(subreddit: Dict[str, Any]) -> str:
    """Render single subreddit card"""

    # Calculate confidence tier
    confidence = subreddit.get('confidence_score', 0)
    tier = 'high' if confidence >= 0.8 else 'medium' if confidence >= 0.6 else 'low'

    # Format subscribers
    subs = subreddit.get('subscribers', 0)
    if subs >= 1_000_000:
        subs_formatted = f"{subs / 1_000_000:.1f}M"
    elif subs >= 1_000:
        subs_formatted = f"{subs / 1_000:.1f}K"
    else:
        subs_formatted = str(subs)

    return f"""
    <div class="subreddit-card">
      <div class="confidence-badge confidence-{tier}">
        {int(confidence * 100)}% match
      </div>

      <div class="subscribers">
        <svg class="icon" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"/>
        </svg>
        <span>{subs_formatted}</span>
      </div>

      <div class="content">
        <h3>r/{subreddit['name']}</h3>
        <p>{subreddit.get('description', 'No description available')}</p>
      </div>
    </div>
    """

def render_subreddit_grid(subreddits: List[Dict[str, Any]]) -> str:
    """Render grid of subreddit cards"""

    cards = ''.join(render_subreddit_card(sr) for sr in subreddits)

    return f"""
    <div class="subreddit-grid">
      <div class="grid-header">
        <span>{len(subreddits)} communities found</span>
      </div>
      <div class="grid-container">
        {cards}
      </div>
    </div>

    <style>
      {SUBREDDIT_GRID_STYLES}
    </style>
    """
```

#### Tool Response Updates

Modify `execute_operation` to return widget references:

```python
# src/server.py - Updated execute_operation
@mcp.tool(description="Execute a Reddit operation with validated parameters")
async def execute_operation(
    operation_id: str,
    parameters: Dict[str, Any],
    ctx: Context = None
) -> Dict[str, Any]:
    """Execute operation and return data with optional widget"""

    operations = {
        "discover_subreddits": discover_subreddits,
        # ... other operations
    }

    if operation_id not in operations:
        return {"success": False, "error": f"Unknown operation: {operation_id}"}

    try:
        # Execute operation
        if operation_id in ["search_subreddit", "fetch_posts", "fetch_multiple", "fetch_comments"]:
            params = {**parameters, "reddit": reddit, "ctx": ctx}
        else:
            params = {**parameters, "ctx": ctx}

        if operation_id in ["discover_subreddits", "fetch_multiple", "fetch_comments"]:
            result = await operations[operation_id](**params)
        else:
            result = operations[operation_id](**params)

        # Add widget rendering for visual display
        widget = None
        if operation_id == "discover_subreddits":
            from src.widgets.subreddit_widgets import render_subreddit_grid
            subreddits = result.get('subreddits', [])
            widget = {
                "uri": "ui://widget/subreddit_grid",
                "mimeType": "text/html+skybridge",
                "content": render_subreddit_grid(subreddits)
            }

        return {
            "success": True,
            "data": result,
            "widget": widget  # Optional widget for visual display
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "recovery": suggest_recovery(operation_id, e)
        }
```

**Total Widget Development Effort**: 7-10 hours (with component reuse)

---

### 3. CSP Configuration

**Objective**: Configure Content Security Policy for widget sandboxing.

**Implementation**:
```python
# src/config.py - Add CSP configuration
CSP_CONFIG = {
    "widget_domains": [
        "i.redd.it",                    # Reddit images
        "external-preview.redd.it",     # Reddit previews
        "www.redditstatic.com"          # Reddit static assets
    ],
    "csp": {
        "script-src": ["'self'", "'unsafe-inline'"],  # Allow inline scripts
        "style-src": ["'self'", "'unsafe-inline'"],   # Allow inline styles
        "img-src": ["'self'", "data:", "https:"],     # Allow all HTTPS images
        "connect-src": ["'self'"],                     # Only same-origin requests
        "font-src": ["'self'", "data:"],              # Allow fonts
        "frame-src": ["'none'"],                       # No iframes
        "object-src": ["'none'"]                       # No plugins
    }
}

# Add to server manifest
MANIFEST = {
    "name": "reddit-research-mcp",
    "version": "1.0.0",
    "display_name": "Reddit Research",
    "description": "Use this when the user wants to research topics on Reddit, discover relevant communities, or analyze Reddit discussions",
    "oauth": {
        "client_id": os.getenv("DESCOPE_PROJECT_ID"),
        "authorization_url": f"{os.getenv('SERVER_URL')}/oauth/authorize",
        "token_url": f"{os.getenv('SERVER_URL')}/oauth/token",
        "scopes": ["read:reddit"]
    },
    "widget_domains": CSP_CONFIG["widget_domains"],
    "csp": CSP_CONFIG["csp"]
}
```

**Effort**: 0.5-1 hour (with LLM)

---

### 4. Metadata Optimization for Discovery

**Objective**: Optimize tool descriptions for ChatGPT's discovery algorithm.

**Current vs. Optimized**:

```python
# BEFORE
@mcp.tool(
    description="Discover available Reddit operations and recommended workflows"
)
def discover_operations(ctx: Context) -> Dict[str, Any]:
    ...

# AFTER
@mcp.tool(
    description="Use this when the user wants to find Reddit communities, research topics on Reddit, or discover relevant subreddits for any subject or question"
)
def discover_operations(ctx: Context) -> Dict[str, Any]:
    ...
```

**Optimization Guidelines**:
1. **Start with "Use this when..."** - Helps ChatGPT understand context
2. **Include synonyms** - "communities", "subreddits", "Reddit forums"
3. **Be specific but not narrow** - Cover related use cases
4. **Avoid generic terms** - Don't say "research" without "Reddit"

**Updated Tool Descriptions**:

```python
# src/server.py - Optimized metadata
@mcp.tool(
    description="Use this when the user wants to discover relevant Reddit communities, find subreddits for research, or identify where people discuss specific topics on Reddit",
    annotations={"readOnlyHint": True}
)
def discover_operations(ctx: Context) -> Dict[str, Any]:
    """Layer 1: Discover Reddit operations"""
    ...

@mcp.tool(
    description="Use this when the user wants to understand the parameters needed for Reddit operations, or needs examples of how to search communities or fetch posts",
    annotations={"readOnlyHint": True}
)
def get_operation_schema(
    operation_id: str,
    include_examples: bool = True,
    ctx: Context = None
) -> Dict[str, Any]:
    """Layer 2: Get operation schema"""
    ...

@mcp.tool(
    description="Use this when the user wants to actually perform Reddit research, search subreddits, fetch posts, analyze comments, or gather community data"
)
async def execute_operation(
    operation_id: str,
    parameters: Dict[str, Any],
    ctx: Context = None
) -> Dict[str, Any]:
    """Layer 3: Execute Reddit operation"""
    ...
```

**Testing Strategy**:
Test with various conversation patterns to ensure app surfaces appropriately:
- "What do people on Reddit think about electric vehicles?"
- "Find me communities discussing machine learning"
- "Show me Reddit discussions about remote work"
- "Research Python frameworks on Reddit"
- "Where can I find people talking about investing on Reddit?"

**Effort**: 1-2 hours (testing requires iteration)

---

### 5. Deployment Configuration

**Objective**: Deploy server to cloud platform with HTTPS.

#### Option A: Render (Recommended)

**Why Render**:
- ✅ Free tier available
- ✅ Automatic HTTPS
- ✅ Simple environment variable management
- ✅ PostgreSQL and Redis available if needed later
- ✅ Good Python support

**Configuration**:
```yaml
# render.yaml
services:
  - type: web
    name: reddit-research-mcp
    env: python
    region: oregon
    plan: free
    buildCommand: "pip install -r requirements.txt"
    startCommand: "python src/server.py --http"
    envVars:
      - key: REDDIT_CLIENT_ID
        sync: false
      - key: REDDIT_CLIENT_SECRET
        sync: false
      - key: REDDIT_USER_AGENT
        value: "RedditMCP:v1.0:reddit-research-mcp"
      - key: DESCOPE_PROJECT_ID
        sync: false
      - key: DESCOPE_BASE_URL
        value: "https://api.descope.com"
      - key: SERVER_URL
        value: "https://mcp.dialog.tools"
      - key: CHROMA_PROXY_URL
        sync: false
      - key: CHROMA_PROXY_API_KEY
        sync: false
    healthCheckPath: /health
```

**Deployment Steps**:
1. Create Render account
2. Connect GitHub repository
3. Create new Web Service
4. Upload `render.yaml`
5. Configure environment variables in dashboard
6. Deploy

#### Option B: Railway

**Why Railway**:
- ✅ Excellent developer experience
- ✅ Automatic HTTPS
- ✅ Simple pricing ($5/month after free tier)
- ✅ Fast deployments

**Configuration**:
```toml
# railway.toml
[build]
builder = "NIXPACKS"
buildCommand = "pip install -r requirements.txt"

[deploy]
startCommand = "python src/server.py --http"
restartPolicyType = "ON_FAILURE"
healthcheckPath = "/health"
healthcheckTimeout = 30

[env]
PORT = "8000"
```

#### Environment Variables Needed
```bash
# Reddit API
REDDIT_CLIENT_ID=your_client_id
REDDIT_CLIENT_SECRET=your_client_secret
REDDIT_USER_AGENT=RedditMCP:v1.0:reddit-research-mcp

# Descope OAuth
DESCOPE_PROJECT_ID=your_project_id
DESCOPE_BASE_URL=https://api.descope.com

# Server Configuration
SERVER_URL=https://your-app.onrender.com  # or railway.app
NODE_ENV=production

# ChromaDB (optional)
CHROMA_PROXY_URL=https://reddit-mcp-vector-db.onrender.com
CHROMA_PROXY_API_KEY=your_proxy_api_key
```

**Effort**: 3-4 hours (including environment setup and testing)

---

## Component Reuse Strategy

### React → Widget Conversion

Our existing frontend has 5 key components that can be directly converted to widgets:

| React Component | Widget Purpose | Conversion Effort | Time Savings |
|----------------|----------------|-------------------|--------------|
| SubredditCard | Display subreddit with confidence | 1-2 hrs | 15-20 hrs |
| SubredditGrid | Grid of subreddit cards | 1-2 hrs | 10-15 hrs |
| RedditQuote | Formatted quote with attribution | 0.5-1 hr | 5-8 hrs |
| SentimentGauge | Visual sentiment indicator | 0.5-1 hr | 5-8 hrs |
| MetricBadge | Metric display badge | 0.5 hr | 2-4 hrs |

**Total Savings**: 37-55 hours → 7-10 hours conversion work

### Conversion Process

#### 1. Extract Styles
```bash
# Option A: Manual conversion (Tailwind → CSS)
# Convert className="p-3 rounded-lg" to style="padding: 0.75rem; border-radius: 0.5rem;"

# Option B: Use Tailwind JIT (recommended)
# Create widget HTML with Tailwind classes
# Run: npx tailwindcss -o widget-styles.css --minify
# Include generated CSS in widget <style> block
```

#### 2. Replace React Logic with Templates
```html
<!-- React (JSX) -->
<h3 className="text-base font-semibold">
  r/{subreddit.name}
</h3>

<!-- Widget (HTML template) -->
<h3 class="text-base font-semibold">
  r/{{name}}
</h3>
```

#### 3. Convert Functions to Server-Side
```typescript
// React (client-side)
const formatSubscribers = (count: number): string => {
  if (count >= 1000000) return `${(count / 1000000).toFixed(1)}M`;
  if (count >= 1000) return `${(count / 1000).toFixed(1)}K`;
  return count.toString();
};

// Python (server-side)
def format_subscribers(count: int) -> str:
    if count >= 1_000_000:
        return f"{count / 1_000_000:.1f}M"
    if count >= 1_000:
        return f"{count / 1_000:.1f}K"
    return str(count)
```

### Example: SubredditCard Conversion

**Original React Component** (102 lines):
```tsx
// frontend/src/components/subreddit/SubredditCard.tsx
export const SubredditCard: React.FC<SubredditCardProps> = ({
  subreddit,
  isSelected,
  onToggle,
}) => {
  const confidenceColor = (score: number) => {
    if (score >= 0.8) return 'bg-success-primary/20 text-success-primary border-success-primary';
    if (score >= 0.6) return 'bg-brand-primary-primary/20 text-brand-primary-primary border-brand-primary-primary';
    return 'bg-grey-tertiary/20 text-grey-secondary border-grey-tertiary';
  };

  // ... component logic

  return (
    <div className={`relative p-3 rounded-lg shadow-md transition-all duration-200 ...`}>
      {/* ... JSX structure ... */}
    </div>
  );
};
```

**Converted Widget** (~50 lines):
```python
# src/widgets/subreddit_widgets.py
def render_subreddit_card(subreddit: Dict[str, Any]) -> str:
    """Render subreddit card widget"""

    # Server-side logic
    confidence = subreddit.get('confidence_score', 0)
    tier = 'high' if confidence >= 0.8 else 'medium' if confidence >= 0.6 else 'low'

    subs = subreddit.get('subscribers', 0)
    subs_formatted = (
        f"{subs / 1_000_000:.1f}M" if subs >= 1_000_000 else
        f"{subs / 1_000:.1f}K" if subs >= 1_000 else
        str(subs)
    )

    # HTML template with inline CSS
    return f"""
    <div class="subreddit-card">
      <div class="confidence-badge confidence-{tier}">
        {int(confidence * 100)}% match
      </div>

      <div class="subscribers">
        <svg class="icon" viewBox="0 0 24 24"><!-- SVG path --></svg>
        <span>{subs_formatted}</span>
      </div>

      <div class="content">
        <h3>r/{subreddit['name']}</h3>
        <p>{subreddit.get('description', 'No description available')}</p>
      </div>
    </div>

    <style>
      .subreddit-card {{
        position: relative;
        padding: 12px;
        border-radius: 8px;
        background: #1a1a1a;
        border: 1px solid #333;
        transition: all 0.2s;
      }}

      .confidence-high {{
        background: rgba(34,197,94,0.2);
        color: #22c55e;
        border: 1px solid #22c55e;
      }}

      /* ... more styles ... */
    </style>
    """
```

**Key Changes**:
- React props → Python function parameters
- JSX → HTML string with f-string interpolation
- Tailwind classes → Inline CSS (or extracted CSS)
- Client logic → Server-side Python functions
- Interactive elements removed (checkboxes, onClick)

---

## Implementation Timeline

### LLM-Assisted Implementation Estimates

With LLM (Claude Code) doing the coding, human time is dramatically reduced:

| Task | Human Manual | LLM-Assisted | Savings |
|------|--------------|--------------|---------|
| HTTP Transport | 2-4 hrs | 0.5-1 hr | 75% |
| Widget Conversion | 7-10 hrs | 1-2 hrs | 85% |
| OAuth Verification | 4-8 hrs | 2-3 hrs | 50% |
| CSP Configuration | 2-3 hrs | 0.5-1 hr | 67% |
| Server Integration | 3-4 hrs | 0.5-1 hr | 80% |
| Deployment | 4-6 hrs | 3-4 hrs | 33% |
| Testing/Iteration | 3-4 hrs | 3-4 hrs | 0% |
| Bug Fixes | 2-3 hrs | 0.5-1 hr | 75% |
| Metadata Optimization | 2 hrs | 1-2 hrs | 25% |
| Documentation | 1 hr | 0.25 hr | 75% |
| **TOTAL** | **27-43 hrs** | **12-18 hrs** | **58%** |

### Week-Long Implementation Plan (Casual Pace)

**Day 1 (2-3 hours): Core Implementation**
- [ ] LLM generates HTTP transport code
- [ ] LLM converts all 5 React components to widgets
- [ ] Human reviews and approves code
- [ ] Local testing of widgets
- [ ] Fix any rendering issues

**Day 2 (2-3 hours): Integration & Deployment**
- [ ] LLM updates `execute_operation` to return widgets
- [ ] LLM creates deployment configuration (render.yaml)
- [ ] Human deploys to Render/Railway
- [ ] Human configures environment variables
- [ ] Verify deployment health check

**Day 3 (2-3 hours): ChatGPT Integration**
- [ ] Human enables ChatGPT Developer Mode
- [ ] Human registers app with staging URL
- [ ] Test basic conversation flows
- [ ] Verify widgets render in ChatGPT sandbox
- [ ] Debug CSP/424 errors if they appear

**Day 4 (2-3 hours): Testing & Iteration**
- [ ] Test all 5 Reddit operations in ChatGPT
- [ ] Try various conversation patterns for discovery
- [ ] LLM optimizes metadata based on what works
- [ ] Human verifies improvements
- [ ] Additional bug fixes

**Day 5 (2 hours): Polish & Documentation**
- [ ] LLM generates final fixes
- [ ] Human deploys to production
- [ ] LLM creates documentation
- [ ] Final verification
- [ ] Ready for users (when directory opens)

**Total Human Time: 10-14 hours over 5 days**

### Weekend Sprint (Intensive)

**Saturday (6-8 hours)**
- Morning (3-4 hrs): Complete implementation & local testing
- Afternoon (3-4 hrs): Deployment & ChatGPT integration

**Sunday (6-8 hours)**
- Morning (3-4 hrs): Comprehensive testing & bug fixes
- Afternoon (3-4 hrs): Optimization & final polish

**Total: 12-16 hours over 2 days**

### Single-Day MVP (Sprint Mode)

If you can dedicate one full day (8-10 hours):
- **Hours 1-2**: Implementation (all code generated by LLM)
- **Hours 3-4**: Deployment & ChatGPT setup
- **Hours 5-6**: Testing & iteration
- **Hours 7-8**: Bug fixes & optimization
- **Hours 9-10**: Polish & documentation

---

## Technical Specifications

### Directory Structure Changes

```
reddit-research-mcp/
├── src/
│   ├── widgets/
│   │   ├── __init__.py
│   │   ├── templates.py              # NEW: HTML templates
│   │   ├── subreddit_widgets.py      # NEW: Subreddit display widgets
│   │   ├── post_widgets.py           # NEW: Post/comment widgets
│   │   └── research_widgets.py       # NEW: Research report widgets
│   ├── config.py                     # MODIFIED: Add CSP config
│   ├── server.py                     # MODIFIED: HTTP mode, widgets
│   └── ... (existing files)
├── render.yaml                       # NEW: Render deployment config
├── railway.toml                      # NEW: Railway deployment config (optional)
└── requirements.txt                  # MODIFIED: Add any new dependencies
```

### Dependencies to Add

```txt
# requirements.txt additions
starlette>=0.27.0      # For CORS middleware (may already be included)
uvicorn>=0.23.0        # HTTP server (may already be included with FastMCP)
```

### Environment Variables

```bash
# .env.production (for deployment)
REDDIT_CLIENT_ID=your_client_id
REDDIT_CLIENT_SECRET=your_client_secret
REDDIT_USER_AGENT=RedditMCP:v1.0:reddit-research-mcp
DESCOPE_PROJECT_ID=your_descope_project_id
DESCOPE_BASE_URL=https://api.descope.com
SERVER_URL=https://mcp.dialog.tools
CHROMA_PROXY_URL=https://reddit-mcp-vector-db.onrender.com
CHROMA_PROXY_API_KEY=your_chroma_api_key
NODE_ENV=production
PORT=8000
```

### Testing Checklist

#### Local Testing (Before Deployment)
- [ ] HTTP server starts successfully on port 8000
- [ ] Health check endpoint returns 200: `curl http://localhost:8000/health`
- [ ] Server info endpoint returns correct data: `curl http://localhost:8000/server-info`
- [ ] OAuth endpoints are accessible
- [ ] All widgets render without errors
- [ ] Tool execution returns widget data

#### Deployment Testing
- [ ] App deploys successfully to hosting platform
- [ ] HTTPS certificate is active
- [ ] Health check passes in production
- [ ] Environment variables are configured correctly
- [ ] OAuth flow works with production URL
- [ ] Logs show no errors

#### ChatGPT Integration Testing
- [ ] App registers in ChatGPT Developer Mode
- [ ] Discovery triggers on relevant conversations
- [ ] All 5 operations execute successfully
- [ ] Widgets render in ChatGPT sandbox (no CSP errors)
- [ ] Images load (Reddit thumbnails)
- [ ] Links work (external navigation)
- [ ] OAuth prompts correctly when needed

#### Discovery Testing (Conversation Patterns)
Test these phrases to verify app surfaces appropriately:
- [ ] "What do people on Reddit think about [topic]?"
- [ ] "Find me Reddit communities about [topic]"
- [ ] "Show me discussions about [topic] on Reddit"
- [ ] "Research [topic] on Reddit"
- [ ] "Where can I find people talking about [topic] on Reddit?"

---

## Decision Points & Considerations

### 1. Styling Approach

**Decision**: How to convert Tailwind CSS to widget CSS?

**Options**:
- **A. Manual Conversion** (inline styles)
  - Pros: Full control, no build step
  - Cons: Time-consuming, verbose
  - Best for: Quick MVP

- **B. Tailwind JIT Extraction** (generate CSS file)
  - Pros: Clean, maintainable, familiar
  - Cons: Requires build step
  - Best for: Production-ready widgets

- **C. Hybrid** (Tailwind for complex, inline for simple)
  - Pros: Balanced approach
  - Cons: Inconsistent patterns
  - Best for: Iterative development

**Recommendation**: Start with **Option A** for MVP, migrate to **Option B** for production.

### 2. Widget Interactivity

**Decision**: Should widgets have interactive elements?

**Constraints**:
- ChatGPT widgets run in sandboxed iframes
- Limited JavaScript execution
- Must use `window.parent.postMessage()` for tool calls

**Options**:
- **A. Static Widgets Only**
  - Pros: Simple, reliable, fast to build
  - Cons: Less engaging
  - Best for: MVP

- **B. Basic Interactivity** (expand/collapse, tooltips)
  - Pros: Better UX
  - Cons: More complex, potential CSP issues
  - Best for: Production

**Recommendation**: **Option A** for initial release, add interactivity in Phase 2.

### 3. OAuth Requirement

**Decision**: Should all operations require OAuth?

**Current State**: OAuth is configured but may not be strictly required for read-only Reddit operations.

**Options**:
- **A. No OAuth Required**
  - Pros: Frictionless user experience
  - Cons: Rate limits may affect users

- **B. Optional OAuth** (prompt when rate limited)
  - Pros: Best of both worlds
  - Cons: Complex logic

- **C. Always Require OAuth**
  - Pros: Consistent experience, higher rate limits
  - Cons: Friction for new users

**Recommendation**: **Option B** - Allow anonymous use until rate limited, then prompt for OAuth.

### 4. Deployment Platform

**Decision**: Which cloud platform?

**Options Comparison**:

| Feature | Render | Railway | Fly.io |
|---------|--------|---------|--------|
| Free Tier | ✅ Yes | ✅ Yes ($5 credit) | ✅ Yes (limited) |
| Pricing | $7/mo after free | $5/mo | Usage-based |
| Ease of Use | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| Python Support | ✅ Native | ✅ Native | ✅ Dockerfile |
| HTTPS | ✅ Automatic | ✅ Automatic | ✅ Automatic |
| Environment Vars | ✅ Simple | ✅ Simple | ✅ Simple |
| Databases | ✅ PostgreSQL | ✅ PostgreSQL | ✅ PostgreSQL |

**Recommendation**: **Render** for simplicity and free tier, **Railway** for best DX.

### 5. Phased Rollout

**Decision**: Should we implement all features at once or in phases?

**Phase 1: MVP** (Week 1)
- HTTP transport
- Basic widgets (SubredditCard, RedditQuote)
- Simple deployment
- Basic discovery metadata

**Phase 2: Enhanced Widgets** (Week 2-3)
- All 5 widgets fully polished
- Interactive elements
- Optimized CSS
- Comprehensive testing

**Phase 3: Production Ready** (Week 4)
- Advanced features (if needed)
- Performance optimization
- Monitoring and analytics
- Documentation for app directory submission

**Recommendation**: **Phase 1 → Test → Phase 2** approach to validate concept quickly.

---

## Success Criteria

### MVP Success Metrics
- [ ] App deploys successfully with HTTPS
- [ ] All 5 Reddit operations work in ChatGPT
- [ ] At least 2 widgets render correctly (SubredditCard, RedditQuote)
- [ ] App surfaces in 3+ conversation patterns
- [ ] No critical bugs or CSP errors
- [ ] OAuth flow works (if implemented)

### Production Ready Metrics
- [ ] All 5 widgets fully implemented and polished
- [ ] App surfaces reliably in target conversations
- [ ] Widget rendering performance < 2 seconds
- [ ] Zero CSP/424 errors in testing
- [ ] Comprehensive documentation complete
- [ ] Ready for app directory submission

### User Experience Goals
- [ ] Users can discover Reddit communities through conversation
- [ ] Widgets provide clear, actionable information
- [ ] Visual design is clean and professional
- [ ] App feels integrated with ChatGPT (not jarring)
- [ ] Operations complete in < 5 seconds

---

## Risk Assessment

### High Risk (Requires Mitigation)

**1. CSP/424 Errors During Widget Rendering**
- **Likelihood**: Medium-High
- **Impact**: High (breaks user experience)
- **Mitigation**:
  - Test widgets in isolation first
  - Start with simple widgets, add complexity gradually
  - Keep detailed logs of CSP issues
  - Reference Apps SDK guide for troubleshooting

**2. Discovery Not Surfacing App**
- **Likelihood**: Medium
- **Impact**: High (users can't find app)
- **Mitigation**:
  - Test 15+ conversation patterns
  - Iterate on metadata descriptions
  - Use "Use this when..." format consistently
  - Monitor which patterns work best

**3. Apps SDK Changes During Development**
- **Likelihood**: Medium (SDK is 1 month old)
- **Impact**: Medium (may require rework)
- **Mitigation**:
  - Monitor OpenAI announcements
  - Join developer community/forums
  - Keep architecture flexible

### Medium Risk

**4. OAuth Configuration Issues**
- **Likelihood**: Low-Medium
- **Impact**: Medium
- **Mitigation**:
  - Test OAuth flow early
  - Use existing Descope configuration
  - Have fallback to anonymous mode

**5. Widget Performance in ChatGPT Sandbox**
- **Likelihood**: Low
- **Impact**: Medium
- **Mitigation**:
  - Keep widgets lightweight
  - Optimize CSS
  - Minimize external dependencies

### Low Risk

**6. Deployment Platform Issues**
- **Likelihood**: Low
- **Impact**: Low-Medium
- **Mitigation**:
  - Use well-documented platforms (Render/Railway)
  - Have backup platform ready
  - Test deployment early

---

## Next Steps

### Immediate Actions (When Ready to Start)

1. **Review OpenAI Apps SDK Guide**
   - Location: `/ai-docs/openai-apps-sdk-comprehensive-guide.md`
   - Read sections on widget development and CSP configuration
   - Review real-world examples

2. **Set Up Development Environment**
   - Ensure FastMCP is up to date
   - Test HTTP mode locally: `python src/server.py --http`
   - Verify all dependencies are installed

3. **Choose Deployment Platform**
   - Create account on Render or Railway
   - Set up GitHub repository connection
   - Prepare environment variables

4. **Begin Implementation**
   - Start with HTTP transport (fastest win)
   - Convert SubredditCard widget first (most visible)
   - Test locally before deploying

### Questions to Resolve

1. **OAuth Strategy**: Do we require OAuth for all operations or make it optional?
2. **Styling Approach**: Manual CSS conversion or Tailwind extraction?
3. **Deployment Platform**: Render vs. Railway?
4. **Interactive Widgets**: MVP static or add basic interactivity?
5. **Phased Rollout**: All features at once or MVP → iterate?

### Resources Created

1. **OpenAI Apps SDK Guide**: `/ai-docs/openai-apps-sdk-comprehensive-guide.md`
2. **This Specification**: `/specs/openai-apps-sdk-compatibility.md`
3. **Existing React Components**: `/frontend/src/components/`
4. **MCP Server**: `/src/server.py`

---

## Appendix

### Useful Links

- **OpenAI Apps SDK Docs**: `developers.openai.com/apps-sdk`
- **MCP Specification**: `modelcontextprotocol.io`
- **FastMCP Documentation**: `github.com/jlowin/fastmcp`
- **Render Documentation**: `render.com/docs`
- **Railway Documentation**: `docs.railway.app`

### File Paths Reference

**MCP Server**:
- Main server: `/src/server.py`
- Config: `/src/config.py`
- Tools: `/src/tools/*.py`
- Resources: `/src/resources.py`

**Frontend Components** (for conversion):
- SubredditCard: `/frontend/src/components/subreddit/SubredditCard.tsx`
- SubredditGrid: `/frontend/src/components/subreddit/SubredditGrid.tsx`
- RedditQuote: `/frontend/src/components/visualization/RedditQuote.tsx`
- SentimentGauge: `/frontend/src/components/visualization/SentimentGauge.tsx`
- MetricBadge: `/frontend/src/components/visualization/MetricBadge.tsx`

**Types** (shared):
- `/shared/types.ts` - Contains `SubredditOption`, `RedditPost`, etc.

### Contact Points for Implementation

When ready to implement:
1. Resume conversation with Claude Code
2. Reference this spec file
3. Provide decision answers for questions listed above
4. Begin with Day 1 implementation plan

---

**End of Specification**

*Last Updated: November 10, 2025*
*Status: Ready for Implementation*
*Estimated Effort: 12-18 hours (LLM-assisted)*