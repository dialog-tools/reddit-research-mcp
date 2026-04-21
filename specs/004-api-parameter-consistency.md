# API Parameter Consistency Improvements

**Status:** Draft
**Created:** 2025-12-09
**Owner:** Engineering Team
**Priority:** Medium

## Executive Summary

This specification addresses parameter naming inconsistencies in the Reddit MCP server API that cause LLM agents to waste turns calling `get_operation_schema()` mid-workflow. The fix involves standardizing parameter names across operations and providing self-documenting response objects.

## Problem Statement

### Evidence from Production Trace

A conversation trace (`trace_dd04c0dd-d873-43ce-9cb9-9162c7b94328.json`) revealed the following issue:

1. Agent called `search_subreddit` and received posts with `id` field
2. Agent attempted `fetch_comments` with `{"post_id": "1pb9xm3", "limit": 100}`
3. **FAILURE**: Operation expects `submission_id` and `comment_limit`
4. Agent called `get_operation_schema("fetch_comments")` to discover correct names
5. Agent retried with `{"submission_id": "1pb9xm3", "comment_limit": 100}`

**Impact:**
- 1 extra LLM turn (~$0.01-0.05 per session)
- ~5 seconds additional latency
- Wasted context window tokens

### Root Cause Analysis

| Source | Field Name | Target Operation | Expected Name |
|--------|-----------|------------------|---------------|
| `RedditPost` model | `id` | `fetch_comments` | `submission_id` |
| LLM assumption | `limit` | `fetch_comments` | `comment_limit` |
| `search_subreddit` | `limit` param | `fetch_comments` | `comment_limit` |

The inconsistency exists because:
1. `RedditPost.id` uses Reddit's shorthand, but `fetch_comments` uses Reddit's API terminology (`submission_id`)
2. Most operations use `limit`, but `fetch_comments` uses `comment_limit` to be explicit

## Proposed Solution - Three Phases

### Phase 1: Self-Documenting Responses (Non-Breaking)

**Goal:** Help LLMs understand how to use returned data in subsequent operations without changing parameter names.

**Changes to `src/tools/search.py` and `src/tools/posts.py`:**

Add a `next_operations` hint to each returned post:

```python
# In search_in_subreddit() result building (line ~96)
results.append({
    **RedditPost(...).model_dump(),
    "next_operations": {
        "fetch_comments": {
            "submission_id": submission.id,
            "comment_limit": 100  # suggested default
        }
    }
})
```

**Rationale:** LLMs can copy-paste the `next_operations` payload directly into `execute_operation`, eliminating guesswork.

**Files to modify:**
- `/src/tools/search.py` - `search_in_subreddit()` function (lines 94-106)
- `/src/tools/posts.py` - `fetch_subreddit_posts()` function (lines 39-70)
- `/src/tools/posts.py` - `fetch_multiple_subreddits()` function (lines 154-200)

---

### Phase 2: Standardize Parameter Names (Breaking Change)

**Goal:** Make all operations use consistent parameter naming conventions.

**Proposed Standard:**

| Current Name | New Standard Name | Affected Operations |
|--------------|-------------------|---------------------|
| `submission_id` | `post_id` | `fetch_comments` |
| `comment_limit` | `limit` | `fetch_comments` |
| `subreddit_name` | `subreddit` | All operations |
| `limit_per_subreddit` | `limit` | `fetch_multiple` |

**Changes to `/src/tools/comments.py`:**

```python
# Before (line 53-59)
async def fetch_submission_with_comments(
    reddit: praw.Reddit,
    submission_id: Optional[str] = None,
    url: Optional[str] = None,
    comment_limit: int = 100,
    ...
)

# After
async def fetch_submission_with_comments(
    reddit: praw.Reddit,
    post_id: Optional[str] = None,  # Renamed
    url: Optional[str] = None,
    limit: int = 100,  # Renamed
    ...
)
```

**Changes to `/src/server.py`:**

Update the `SCHEMAS` dict for `fetch_comments` (lines 402-431):

```python
"fetch_comments": {
    "description": "Get complete comment tree for a post",
    "parameters": {
        "post_id": {  # Was submission_id
            "type": "string",
            "required_one_of": ["post_id", "url"],
            "description": "Reddit post ID (e.g., '1abc234')"
        },
        "limit": {  # Was comment_limit
            "type": "integer",
            "default": 100,
            ...
        }
    }
}
```

**Migration:** Remove the existing alias in `execute_operation` (line 620):
```python
param_aliases = {"subreddit": "subreddit_name"}  # Remove this after standardization
```

**Files to modify:**
- `/src/tools/comments.py` - Function signature (lines 53-59)
- `/src/server.py` - SCHEMAS dict (lines 402-431)
- `/src/server.py` - execute_operation aliases (lines 619-623) - can be removed
- `/src/models.py` - Consider renaming `RedditPost.id` if needed

---

### Phase 3: Workflow Hints in Discovery (Enhancement)

**Goal:** Provide parameter mapping hints in `discover_operations()` response.

**Changes to `/src/server.py` lines 181-210:**

```python
def discover_operations(ctx: Context) -> Dict[str, Any]:
    return {
        "operations": { ... },
        "recommended_workflows": { ... },

        # NEW: Help LLMs understand parameter flow
        "parameter_conventions": {
            "post_id": "Use the 'id' field from any RedditPost in responses",
            "limit": "Maximum items to return (consistent across all operations)",
            "subreddit": "Community name without 'r/' prefix"
        },

        "next_step": "Use get_operation_schema() to understand requirements"
    }
```

**Files to modify:**
- `/src/server.py` - `discover_operations()` function (lines 175-210)

---

## Implementation Order

| Phase | Scope | Breaking? | Effort | Impact |
|-------|-------|-----------|--------|--------|
| 1 | Self-documenting responses | No | Small | High - immediate fix |
| 2 | Standardize names | Yes | Medium | High - long-term consistency |
| 3 | Discovery hints | No | Small | Medium - improved DX |

**Recommended approach:** Implement Phase 1 first for immediate benefit, then Phase 2 in a major version bump.

---

## Testing Strategy

### Phase 1 Tests
```python
def test_search_results_include_next_operations():
    result = search_in_subreddit("python", "async", reddit, limit=1)
    post = result["results"][0]
    assert "next_operations" in post
    assert "fetch_comments" in post["next_operations"]
    assert "submission_id" in post["next_operations"]["fetch_comments"]

def test_next_operations_can_be_used_directly():
    search_result = search_in_subreddit("python", "async", reddit, limit=1)
    params = search_result["results"][0]["next_operations"]["fetch_comments"]
    comments_result = await fetch_submission_with_comments(reddit=reddit, **params)
    assert "comments" in comments_result
```

### Phase 2 Tests
```python
def test_fetch_comments_accepts_post_id():
    result = await fetch_submission_with_comments(reddit=reddit, post_id="abc123", limit=10)
    assert result is not None

def test_fetch_comments_rejects_old_param_names():
    with pytest.raises(TypeError):
        await fetch_submission_with_comments(reddit=reddit, submission_id="abc123")
```

---

## Context for New Agents

### Project Overview
This is a Reddit MCP (Model Context Protocol) server built with FastMCP 2.0. It provides a three-layer architecture:
1. `discover_operations()` - List available operations
2. `get_operation_schema()` - Get parameter requirements
3. `execute_operation()` - Execute with parameters

### Key Files
- `/src/server.py` - Main server with three-layer tools (893 lines)
- `/src/tools/search.py` - Search within subreddits
- `/src/tools/posts.py` - Fetch posts from subreddits
- `/src/tools/comments.py` - Fetch comments for posts
- `/src/models.py` - Pydantic models including `RedditPost`

### Current Alias Handling
`/src/server.py` lines 619-623 has basic alias normalization:
```python
param_aliases = {"subreddit": "subreddit_name"}
for alias, canonical in param_aliases.items():
    if alias in parameters and canonical not in parameters:
        parameters[canonical] = parameters.pop(alias)
```

### Response Model
`RedditPost` (`/src/models.py` lines 6-18):
```python
class RedditPost(BaseModel):
    id: str  # This is what we return
    title: str
    author: str
    subreddit: str
    score: int
    ...
```

### Running Tests
```bash
cd /Users/chrisivester/Documents/mbp-obsidian-vault/02-Projects/software-projects/MCP/reddit-mcp-poc/reddit-research-mcp
source .venv/bin/activate
pytest tests/
```

---

## Success Metrics

- **Primary:** Zero failed `execute_operation` calls due to parameter naming in production traces
- **Secondary:** 50% reduction in `get_operation_schema` calls during multi-step workflows
- **Tertiary:** Improved developer experience scores in feedback
