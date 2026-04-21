# FastMCP 2 to 3 Migration Summary

Synthesized from official FastMCP documentation at https://gofastmcp.com (scraped 2026-02-18).

---

## 1. All Breaking Changes

### 1.1 Import Change (Most Common)
For servers that were using the MCP SDK's bundled FastMCP, the primary change is:
```python
# Before (MCP SDK bundled version)
from mcp.server.fastmcp import FastMCP

# After (standalone FastMCP 3)
from fastmcp import FastMCP
```

### 1.2 Transport/Server Settings Removed from Constructor
`FastMCP()` no longer accepts transport configuration kwargs. These must be passed to `run()` or set via environment variables.

**Removed kwargs:**
- `host`, `port`, `log_level`, `debug`, `sse_path`, `streamable_http_path`, `json_response`, `stateless_http` -> pass to `run()`, `run_http_async()`, or `http_app()`
- `message_path` -> set via `FASTMCP_MESSAGE_PATH` environment variable only
- `on_duplicate_tools`, `on_duplicate_resources`, `on_duplicate_prompts` -> consolidated into `on_duplicate=` parameter
- `tool_serializer` -> return `ToolResult` from your tools instead
- `include_tags` / `exclude_tags` -> use `server.enable(tags=..., only=True)` / `server.disable(tags=...)` after construction
- `tool_transformations` -> use `server.add_transform(ToolTransform(...))` after construction

### 1.3 Listing Methods Renamed and Return Lists
| Before (v2) | After (v3) | Return type change |
|-------------|------------|-------------------|
| `get_tools()` | `list_tools()` | dict -> list |
| `get_resources()` | `list_resources()` | dict -> list |
| `get_prompts()` | `list_prompts()` | dict -> list |
| `get_resource_templates()` | `list_resource_templates()` | dict -> list |

### 1.4 Prompts Use Message Class
```python
# Before
from mcp.types import PromptMessage, TextContent
return PromptMessage(role="user", content=TextContent(type="text", text="Hello"))

# After
from fastmcp.prompts import Message
return Message("Hello")
```
Raw dicts are no longer accepted. v3 requires typed `Message` objects or plain strings.

### 1.5 Context State Methods Are Now Async
```python
# Before (sync)
ctx.set_state("key", "value")
value = ctx.get_state("key")

# After (async)
await ctx.set_state("key", "value")
value = await ctx.get_state("key")
```
State values must be JSON-serializable by default. Use `serializable=False` for non-serializable values (request-scoped only).

### 1.6 Component enable()/disable() Moved to Server
```python
# Before (on component)
tool.disable()

# After (on server)
server.disable(names={"my_tool"}, components={"tool"})
```

### 1.7 Decorators Return Functions (Not Objects)
`@mcp.tool` now returns the original function, not a `FunctionTool` object. Set `FASTMCP_DECORATOR_MODE=object` for temporary v2 compatibility.

### 1.8 OAuth Storage Backend Changed
Default moved from `DiskStore` to `FileTreeStore` (CVE-2025-69872). Clients re-register automatically on first connection.

### 1.9 Auth Provider Environment Variables Removed
No more `FASTMCP_SERVER_AUTH_*` prefix auto-loading. Pass values explicitly.

### 1.10 WSTransport Removed
Use `StreamableHttpTransport` instead of the deprecated WebSocket transport.

### 1.11 OpenAPI `timeout` Parameter Removed
Configure timeout on the httpx client directly.

### 1.12 Metadata Namespace Renamed
`_fastmcp` -> `fastmcp` in component `meta` dicts. `include_fastmcp_meta` parameter removed.

### 1.13 Server Banner Env Var Renamed
`FASTMCP_SHOW_CLI_BANNER` -> `FASTMCP_SHOW_SERVER_BANNER`

### 1.14 Background Tasks Require Optional Dependency
Install with `pip install "fastmcp[tasks]"` if using `task=True` or `TaskConfig`.

### 1.15 Repository Moved
`jlowin/fastmcp` -> `PrefectHQ/fastmcp` (GitHub auto-redirects).

---

## 2. New APIs and Features

### 2.1 New in v3.0.0
- **Session State**: `ctx.set_state()` / `ctx.get_state()` / `ctx.delete_state()` -- persistent state across tool calls within a session, backed by pluggable storage
- **Component Visibility**: Server-level `mcp.enable()` / `mcp.disable()` with key, tag, and type targeting; per-session visibility via context
- **Versioning**: Tools, resources, and prompts support version identifiers (`version=` parameter)
- **Pagination**: `list_page_size` parameter on `FastMCP()` constructor for paginated list responses
- **Tool Timeouts**: `timeout=` parameter on `@mcp.tool` decorator
- **ResourceResult**: Full control over resource responses with multiple content items and metadata
- **PromptResult**: Full control over prompt responses with metadata
- **Message class**: Simplified prompt message creation (`from fastmcp.prompts import Message`)
- **Transport property**: `ctx.transport` to detect STDIO/SSE/HTTP
- **Custom Routes**: `@mcp.custom_route()` for health checks and auxiliary HTTP endpoints
- **Provider-based Architecture**: Proxy and OpenAPI modules moved under `providers`
- **`create_proxy()`**: Replaces `FastMCP.as_proxy()`
- **Change Notifications**: `ctx.send_notification()` for manual list change notifications
- **Dependency Injection**: `CurrentContext()` dependency (preferred over type-hint injection)

### 2.2 Previously Added (v2.x, still relevant)
- **Client Elicitation** (v2.10.0): `ctx.elicit()` for interactive user input
- **Structured Output** (v2.10.0): Automatic structured content alongside traditional content
- **Output Schemas** (v2.10.0): JSON schemas for tool return types
- **Strict Input Validation** (v2.13.0): `strict_input_validation=True`
- **Parameter Descriptions** (v2.11.0): `Annotated[str, "description"]` shorthand
- **Hidden Parameters** (v2.14.0): `Depends()` for dependency injection
- **Query Parameters** (v2.13.0): RFC 6570 form-style query parameters in resource templates
- **Icons** (v2.13.0): Visual icons for servers, tools, resources, prompts
- **MCP Annotations**: `readOnlyHint`, `destructiveHint`, `idempotentHint`, `openWorldHint`

---

## 3. Deprecated Features (Still Work, Emit Warnings)

| Deprecated | Replacement |
|-----------|-------------|
| `main.mount(subserver, prefix="api")` | `main.mount(subserver, namespace="api")` |
| `main.import_server(subserver)` | `main.mount(subserver)` |
| `from fastmcp.server.proxy import FastMCPProxy` | `from fastmcp.server.providers.proxy import FastMCPProxy` |
| `from fastmcp.server.openapi import FastMCPOpenAPI` | `from fastmcp.server.providers.openapi import OpenAPIProvider` |
| `FastMCPOpenAPI(spec, client)` | `FastMCP("name", providers=[OpenAPIProvider(spec, client)])` |
| `mcp.add_tool_transformation("name", config)` | `mcp.add_transform(ToolTransform({"name": config}))` |
| `FastMCP.as_proxy("url")` | `from fastmcp.server import create_proxy; create_proxy("url")` |
| `FASTMCP_DECORATOR_MODE=object` | Will be removed in future release |
| `enabled=` on `@mcp.tool`/`@mcp.resource`/`@mcp.prompt` | `mcp.enable()`/`mcp.disable()` at server level |

---

## 4. Removed Features (Were Deprecated in v2.14.0)

- `BearerAuthProvider` -> use `JWTVerifier`
- `Context.get_http_request()` -> use `get_http_request()` from dependencies
- `from fastmcp import Image` -> use `from fastmcp.utilities.types import Image`
- `FastMCP(dependencies=[...])` -> use `fastmcp.json` configuration
- `FastMCPProxy(client=...)` -> use `client_factory=lambda: ...`
- `output_schema=False` -> use `output_schema=None`

---

## 5. Step-by-Step Migration Checklist

### Phase 1: Install and Import
- [ ] Upgrade: `pip install --upgrade fastmcp` or `uv add --upgrade fastmcp`
- [ ] Update version pin to `fastmcp>=3.0.0,<4` in pyproject.toml/requirements
- [ ] Change imports: `from mcp.server.fastmcp import FastMCP` -> `from fastmcp import FastMCP`
- [ ] If using prompts: `from fastmcp.prompts import Message` (replaces `mcp.types.PromptMessage`)

### Phase 2: Constructor and Run
- [ ] Remove transport kwargs from `FastMCP()` constructor (`host`, `port`, `log_level`, `debug`, etc.)
- [ ] Move transport kwargs to `mcp.run(transport="http", host=..., port=...)` or environment variables
- [ ] Update `on_duplicate_tools`/`on_duplicate_resources`/`on_duplicate_prompts` if set in constructor
- [ ] Remove `tool_serializer` from constructor; use `ToolResult` returns instead
- [ ] Remove `include_tags`/`exclude_tags` from constructor; use `server.enable()`/`server.disable()` after construction

### Phase 3: Component APIs
- [ ] Rename `get_tools()` -> `list_tools()` (returns list, not dict)
- [ ] Rename `get_resources()` -> `list_resources()` (returns list, not dict)
- [ ] Rename `get_prompts()` -> `list_prompts()` (returns list, not dict)
- [ ] Rename `get_resource_templates()` -> `list_resource_templates()` (returns list, not dict)
- [ ] Update any code that indexes listing results by name (use list comprehension/next() instead)

### Phase 4: Prompts
- [ ] Replace `PromptMessage` with `Message` from `fastmcp.prompts`
- [ ] Replace raw dict returns from prompt functions with `Message` objects
- [ ] Replace `TextContent` wrapping with plain strings in `Message()`

### Phase 5: Context
- [ ] Add `await` to all `ctx.set_state()` and `ctx.get_state()` calls
- [ ] Ensure state values are JSON-serializable (or use `serializable=False`)
- [ ] Move `tool.disable()` / `tool.enable()` calls to `server.disable()` / `server.enable()`

### Phase 6: Auth and Transport
- [ ] Replace `WSTransport` with `StreamableHttpTransport`
- [ ] Remove `FASTMCP_SERVER_AUTH_*` env var reliance; pass auth config explicitly
- [ ] If using `DiskStore` for OAuth, migrate to `FileTreeStore`

### Phase 7: Cleanup (Optional)
- [ ] Update deprecated `import_server()` -> `mount()`
- [ ] Update deprecated `prefix=` -> `namespace=` in `mount()`
- [ ] Update proxy/OpenAPI import paths to new `providers` module
- [ ] Replace `FastMCPOpenAPI` with `FastMCP` + `OpenAPIProvider`
- [ ] Replace `FastMCP.as_proxy()` with `create_proxy()`
- [ ] Update metadata key from `_fastmcp` to `fastmcp` in any meta dict access
- [ ] Update `FASTMCP_SHOW_CLI_BANNER` env var to `FASTMCP_SHOW_SERVER_BANNER`
- [ ] If using background tasks, add `pip install "fastmcp[tasks]"` to dependencies

---

## 6. Gotchas and Common Pitfalls

1. **`pip install fastmcp` won't upgrade** -- You must explicitly use `--upgrade` flag or update your version pin.

2. **Decorators return functions now** -- If you access `.name` or `.description` on a decorated function, it will fail. Set `FASTMCP_DECORATOR_MODE=object` as a temporary workaround, but plan to remove this.

3. **State is now async** -- Forgetting to `await` ctx.get_state()/set_state() will return a coroutine object instead of the actual value, leading to subtle bugs.

4. **Listing methods return lists, not dicts** -- Code like `tools["my_tool"]` will raise `TypeError`. Use `next((t for t in tools if t.name == "my_tool"), None)` instead.

5. **Prompt dicts no longer work** -- v2 silently coerced `{"role": "user", "content": "Hello"}` dicts. v3 requires `Message("Hello")`.

6. **Non-serializable state** -- If you store objects like HTTP clients in state without `serializable=False`, you'll get serialization errors. Non-serializable state is request-scoped only.

7. **OAuth re-registration** -- After upgrading, clients using default OAuth storage will need to re-register on their first connection (happens automatically).

8. **`on_duplicate` consolidation** -- If you had different duplicate handling per component type, be aware they've been consolidated in the constructor (though per-type options still work in `FastMCP()`).

9. **Background tasks extra** -- If your server uses `task=True`, you'll get an import error at runtime unless you install `fastmcp[tasks]`.

10. **Repository URL** -- If you reference `jlowin/fastmcp` in `pyproject.toml` git dependencies, update to `PrefectHQ/fastmcp`. GitHub redirects work but are not guaranteed forever.
