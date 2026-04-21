# FastMCP 3 Migration Plan

## Overview

Migration of the Reddit Research MCP server from FastMCP 2.x (`>=2.13.1`) to FastMCP 3.x. Based on analysis of the full codebase and the official FastMCP 3 upgrade guide.

## Risk Assessment Summary

| Risk Level | Count | Items |
|------------|-------|-------|
| No change needed | 5 | Server init, `@mcp.tool`, `@mcp.resource`, `@mcp.prompt` decorators, `mcp.run()` |
| Low risk (drop-in fix) | 4 | Dependency version bump, `Message` import (already correct), `Context` injection (already compatible), annotations dict syntax |
| Medium risk (code changes) | 3 | Auth dependency helpers, custom auth verifier, decorator return behavior |
| Not applicable | 6 | WSTransport, OpenAPI, ctx.set_state/get_state, tag filtering constructor args, `import_server`, `as_proxy` |

**Overall complexity: LOW-MEDIUM.** Most of the codebase uses FastMCP APIs that are unchanged or backward-compatible in v3.

---

## Detailed Migration Map

### 1. Dependency Version Bump
**Risk: LOW | Files: `pyproject.toml`**

```toml
# Before
dependencies = [
    "fastmcp>=2.13.1",
]

# After
dependencies = [
    "fastmcp>=3.0.0,<4",
]
```

### 2. Imports - What Changes and What Doesn't

#### No changes needed (already v3-compatible):
| Import | File(s) | Status |
|--------|---------|--------|
| `from fastmcp import FastMCP, Context` | `src/server.py` | Compatible (legacy type-hint injection still works) |
| `from fastmcp.prompts import Message` | `src/server.py` | Already using the v3 `Message` class |
| `from fastmcp import Context` | All tool files, tests | Compatible |
| `from fastmcp.server.auth.providers.jwt import JWTVerifier` | `src/auth/multi_issuer_verifier.py` | Compatible (same location in v3) |
| `from fastmcp.server.auth import AccessToken` | `src/auth/multi_issuer_verifier.py` | Compatible |
| `from fastmcp.utilities.logging import get_logger` | `src/auth/multi_issuer_verifier.py` | Compatible |

#### Needs verification (may have moved in v3):
| Import | File | Action |
|--------|------|--------|
| `from fastmcp.server.auth.providers.descope import DescopeProvider` | `src/server.py` | Verify `DescopeProvider` still exists at this path in v3. This is a third-party auth provider - check if it was moved or renamed. |
| `from fastmcp.server.dependencies import get_http_headers, get_access_token` | `src/tools/feed.py` | These function-style helpers still exist in v3 per the docs. **Compatible.** New v3 style prefers `CurrentHeaders()` and `CurrentAccessToken()` dependency injection but the function API is not deprecated. |

### 3. Server Initialization
**Risk: NONE | File: `src/server.py:55-86`**

```python
mcp = FastMCP("Reddit MCP", auth=auth, instructions="""...""")
```

This is fully compatible with v3. The `FastMCP()` constructor still accepts `name`, `auth`, and `instructions`. The breaking changes only affect transport kwargs (`host`, `port`, etc.) which this project doesn't use in the constructor.

### 4. Tool Decorators & Annotations
**Risk: LOW | File: `src/server.py`**

All three tools use this pattern:
```python
@mcp.tool(
    description="...",
    annotations={"readOnlyHint": True}
)
```

This is **fully compatible with v3**. The `@mcp.tool` decorator, `description`, and `annotations` dict syntax all work identically.

**Breaking change to be aware of:** In v3, `@mcp.tool` returns the original function, not a `FunctionTool` object. This project does NOT access component attributes on decorated results, so **no change needed**.

### 5. Context Usage
**Risk: LOW | All tool files**

The project uses two Context patterns:

**Pattern A - Positional required (1 tool):**
```python
def discover_operations(ctx: Context) -> Dict[str, Any]:
```

**Pattern B - Optional keyword (all others):**
```python
async def execute_operation(..., ctx: Context = None) -> Dict[str, Any]:
```

Both patterns work in v3 via "legacy type-hint injection." The v3 docs confirm:
> "For backwards compatibility, you can still access context by simply adding a parameter with the Context type hint."

**Optional improvement:** Could migrate to the new `CurrentContext()` dependency injection style, but this is not required.

### 6. Context Methods
**Risk: NONE**

The only `Context` method used is `ctx.report_progress(progress=, total=, message=)` in 3 places:
- `src/tools/posts.py:216-219`
- `src/tools/comments.py:163-168, 187-192`
- `src/tools/discover.py:372-377`

`report_progress()` is unchanged in v3. **No changes needed.**

Note: `ctx.set_state()` / `ctx.get_state()` became async in v3, but this project doesn't use state methods.

### 7. Resource Definition
**Risk: NONE | File: `src/resources.py`**

```python
@mcp.resource("reddit://server-info")
def get_server_info() -> Dict[str, Any]:
```

Fully compatible with v3. The `@mcp.resource` decorator syntax is unchanged.

### 8. Prompt Definition
**Risk: NONE | File: `src/server.py:895-927`**

```python
@mcp.prompt(
    name="reddit_research",
    description="...",
    tags={"research", "analysis", "comprehensive"}
)
def reddit_research(research_request: str) -> List[Message]:
    return [
        Message(role="user", content=...),
        Message(role="assistant", content=...),
    ]
```

This is **already v3-compatible**:
- Uses `from fastmcp.prompts import Message` (correct v3 import)
- Returns `List[Message]` (correct v3 return type)
- Uses `Message(role=..., content=...)` constructor (correct v3 API, though v3 also allows `Message("text")` shorthand)

### 9. Custom Routes
**Risk: NONE | File: `src/server.py:89-225`**

```python
@mcp.custom_route("/health", methods=["GET"])
async def health_check(request) -> Response:
```

The `@mcp.custom_route` decorator is unchanged in v3. **No changes needed.**

### 10. Authentication Architecture
**Risk: MEDIUM | Files: `src/server.py`, `src/auth/multi_issuer_verifier.py`**

The project uses:
- `DescopeProvider` from `fastmcp.server.auth.providers.descope`
- Custom `MultiIssuerJWTVerifier` extending `JWTVerifier`
- `AccessToken` dataclass

**Key v3 breaking change:** "Auth providers no longer auto-load from env vars."

The project already passes values explicitly to `DescopeProvider`, so this breaking change doesn't apply. However:

**Action items:**
1. Verify `DescopeProvider` still exists in FastMCP 3 at the same import path. This is a less commonly used provider - check the v3 source.
2. Verify `JWTVerifier` base class API hasn't changed (methods like `_get_verification_key()`, `jwt.decode()`, `_extract_scopes()`).
3. Verify `AccessToken` dataclass fields are the same (`token`, `client_id`, `scopes`, `expires_at`, `claims`). The v3 docs confirm these fields exist.

### 11. Dependency Helpers
**Risk: LOW-MEDIUM | File: `src/tools/feed.py`**

```python
from fastmcp.server.dependencies import get_http_headers, get_access_token
```

These function-style helpers still exist in v3. The v3 docs show them at the same import path. **No changes required.**

**Optional v3 upgrade:** Could switch to the new dependency injection style:
```python
from fastmcp.dependencies import CurrentHeaders, CurrentAccessToken
from fastmcp.server.auth import AccessToken

@mcp.tool
async def my_tool(
    headers: dict = CurrentHeaders(),
    token: AccessToken = CurrentAccessToken(),
) -> ...:
```

### 12. Transport / Running
**Risk: NONE | File: `src/server.py:946`**

```python
def main():
    mcp.run()
```

`mcp.run()` defaults to stdio in both v2 and v3. **No changes needed.**

### 13. Tests
**Risk: LOW | Files: `tests/test_tools.py`, `tests/test_phase_2a.py`, `tests/test_context_integration.py`**

Tests mock `Context`:
```python
from fastmcp import Context
mock_context = Mock(spec=Context)
mock_context.report_progress = AsyncMock()
```

This should continue to work since `Context` import path and `report_progress` API are unchanged. However, if `Context` class internals changed, `Mock(spec=Context)` could break.

**Action:** Run the test suite after upgrading and fix any spec-related mock failures.

---

## Migration Steps (Recommended Order)

### Phase 1: Version Bump & Smoke Test
1. Update `pyproject.toml`: `fastmcp>=3.0.0,<4`
2. Run `uv sync` to install FastMCP 3
3. Run `uv run pytest` - identify any immediate import errors or failures
4. Check if `DescopeProvider` import still works

### Phase 2: Fix Any Breaking Issues
5. If `DescopeProvider` moved, update import path
6. If `JWTVerifier` base class changed, update `MultiIssuerJWTVerifier`
7. Fix any test failures from mock spec changes

### Phase 3: Optional Modernization (Non-Breaking)
8. Consider switching `Context` to `CurrentContext()` dependency injection
9. Consider switching `get_http_headers`/`get_access_token` to `CurrentHeaders()`/`CurrentAccessToken()`
10. Consider using new v3 features like `PromptResult`, `ResourceResult`, tool `timeout`, or `version` parameters

---

## Not Applicable to This Project

These v3 breaking changes do NOT affect this codebase:

| Breaking Change | Why N/A |
|----------------|---------|
| Constructor transport kwargs removed | Project doesn't pass `host`, `port`, etc. to `FastMCP()` |
| `ctx.set_state()` / `ctx.get_state()` now async | Not used |
| WSTransport removed | Not used |
| OpenAPI `timeout` removed | Not used |
| `on_duplicate_*` consolidated | Not used in constructor |
| `tool_serializer` removed | Not used |
| `include_tags`/`exclude_tags` constructor change | Not used in constructor |
| `import_server()` -> `mount()` | Not used |
| `FastMCP.as_proxy()` deprecated | Not used |
| Background tasks require optional dep | Not used |
| OAuth storage backend changed | Using Descope, not default OAuth |
| Metadata namespace `_fastmcp` -> `fastmcp` | Not reading component metadata |
| `FASTMCP_SHOW_CLI_BANNER` -> `FASTMCP_SHOW_SERVER_BANNER` | Not used |
| Decorator returns function not component | Not accessing component attributes |

## New v3 Features Worth Considering

| Feature | Benefit for This Project |
|---------|------------------------|
| Tool `timeout` parameter | Could add to `execute_operation` to prevent hanging Reddit API calls |
| Tool/resource `version` parameter | Useful for API versioning as the server evolves |
| `PromptResult` | Could add metadata to the `reddit_research` prompt |
| `CurrentContext()` dependency injection | Cleaner than type-hint injection, makes DI explicit |
| Pagination (`list_page_size`) | Useful if tool/resource lists grow large |
| Session state (async `set_state`/`get_state`) | Could persist user preferences across tool calls in a session |
| Component visibility (`mcp.enable()`/`mcp.disable()`) | Dynamic feature gating based on auth roles |
