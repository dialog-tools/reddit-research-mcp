# MCP Context

Source: https://gofastmcp.com/servers/context

When defining FastMCP tools, resources, resource templates, or prompts, your functions might need to interact with the underlying MCP session or access advanced server capabilities. FastMCP provides the `Context` object for this purpose.

You access Context through FastMCP's dependency injection system. For other injectable values like HTTP requests, access tokens, and custom dependencies, see Dependency Injection.

## What Is Context?

The `Context` object provides a clean interface to access MCP features within your functions, including:

- **Logging**: Send debug, info, warning, and error messages back to the client
- **Progress Reporting**: Update the client on the progress of long-running operations
- **Resource Access**: List and read data from resources registered with the server
- **Prompt Access**: List and retrieve prompts registered with the server
- **LLM Sampling**: Request the client's LLM to generate text based on provided messages
- **User Elicitation**: Request structured input from users during tool execution
- **Session State**: Store data that persists across requests within an MCP session
- **Session Visibility**: Control which components are visible to the current session
- **Request Information**: Access metadata about the current request
- **Server Access**: When needed, access the underlying FastMCP server instance

## Accessing the Context

### Preferred: CurrentContext() Dependency (v2.14+)

```python
from fastmcp import FastMCP
from fastmcp.dependencies import CurrentContext
from fastmcp.server.context import Context

mcp = FastMCP(name="Context Demo")

@mcp.tool
async def process_file(file_uri: str, ctx: Context = CurrentContext()) -> str:
    """Processes a file, using context for logging and resource access."""
    await ctx.info(f"Processing {file_uri}")
    return "Processed file"
```

This works with tools, resources, and prompts:

```python
@mcp.resource("resource://user-data")
async def get_user_data(ctx: Context = CurrentContext()) -> dict:
    await ctx.debug("Fetching user data")
    return {"user_id": "example"}

@mcp.prompt
async def data_analysis_request(dataset: str, ctx: Context = CurrentContext()) -> str:
    return f"Please analyze the following dataset: {dataset}"
```

**Key Points:**

- Dependency parameters are automatically excluded from the MCP schema -- clients never see them.
- Context methods are async, so your function usually needs to be async as well.
- **Each MCP request receives a new context object.** Context is scoped to a single request.
- Context is only available during a request; attempting to use context methods outside a request will raise errors.

### Legacy Type-Hint Injection

For backwards compatibility, you can still access context by simply adding a parameter with the `Context` type hint:

```python
from fastmcp import FastMCP, Context

mcp = FastMCP(name="Context Demo")

@mcp.tool
async def process_file(file_uri: str, ctx: Context) -> str:
    """Context is injected automatically based on the type hint."""
    return "Processed file"
```

### Via get_context() Function (v2.2.11+)

For code nested deeper within your function calls where passing context through parameters is inconvenient:

```python
from fastmcp import FastMCP
from fastmcp.server.dependencies import get_context

mcp = FastMCP(name="Dependency Demo")

async def process_data(data: list[float]) -> dict:
    ctx = get_context()
    await ctx.info(f"Processing {len(data)} data points")

@mcp.tool
async def analyze_dataset(dataset_name: str) -> dict:
    data = load_data(dataset_name)
    await process_data(data)
```

> `get_context()` should only be used within the context of a server request. Calling it outside of a request will raise a `RuntimeError`.

## Context Capabilities

### Logging

```python
await ctx.debug("Starting analysis")
await ctx.info(f"Processing {len(data)} items")
await ctx.warning("Deprecated parameter used")
await ctx.error("Processing failed")
```

### Client Elicitation (v2.10.0+)

Request structured input from clients during tool execution:

```python
result = await ctx.elicit("Enter your name:", response_type=str)
if result.action == "accept":
    name = result.data
```

### LLM Sampling (v2.0.0+)

Request the client's LLM to generate text:

```python
response = await ctx.sample("Analyze this data", temperature=0.7)
```

### Progress Reporting

```python
await ctx.report_progress(progress=50, total=100)  # 50% complete
```

### Resource Access

```python
resources = await ctx.list_resources()
content_list = await ctx.read_resource("resource://config")
content = content_list[0].content
```

### Prompt Access (v2.13.0+)

```python
prompts = await ctx.list_prompts()
result = await ctx.get_prompt("analyze_data", {"dataset": "users"})
messages = result.messages
```

### Session State (v3.0.0+)

Store data that persists across multiple requests within the same MCP session:

```python
from fastmcp import FastMCP, Context

mcp = FastMCP("stateful-app")

@mcp.tool
async def increment_counter(ctx: Context) -> int:
    """Increment a counter that persists across tool calls."""
    count = await ctx.get_state("counter") or 0
    await ctx.set_state("counter", count + 1)
    return count + 1

@mcp.tool
async def get_counter(ctx: Context) -> int:
    """Get the current counter value."""
    return await ctx.get_state("counter") or 0
```

**Method signatures:**

- `await ctx.set_state(key, value, *, serializable=True)`: Store a value in session state
- `await ctx.get_state(key)`: Retrieve a value (returns None if not found)
- `await ctx.delete_state(key)`: Remove a value from session state

State methods are async and require `await`. State expires after 1 day to prevent unbounded memory growth.

#### Non-Serializable Values

By default, state values must be JSON-serializable. For non-serializable values like HTTP clients, pass `serializable=False`:

```python
await ctx.set_state("client", my_http_client, serializable=False)
```

Values stored with `serializable=False` only live for the current MCP request.

#### Custom Storage Backends

For distributed or serverless deployments:

```python
from key_value.aio.stores.redis import RedisStore

mcp = FastMCP("distributed-app", session_state_store=RedisStore(...))
```

### Session Visibility (v3.0.0+)

Tools can customize which components are visible to their current session using `ctx.enable_components()`, `ctx.disable_components()`, and `ctx.reset_visibility()`.

### Change Notifications (v3.0.0+)

```python
import mcp.types

@mcp.tool
async def custom_tool_management(ctx: Context) -> str:
    await ctx.send_notification(mcp.types.ToolListChangedNotification())
    await ctx.send_notification(mcp.types.ResourceListChangedNotification())
    await ctx.send_notification(mcp.types.PromptListChangedNotification())
    return "Notifications sent"
```

### FastMCP Server

```python
@mcp.tool
async def my_tool(ctx: Context) -> None:
    server_name = ctx.fastmcp.name
```

### Transport (v3.0.0+)

The `ctx.transport` property indicates which transport is being used:

```python
@mcp.tool
def connection_info(ctx: Context) -> str:
    if ctx.transport == "stdio":
        return "Connected via STDIO"
    elif ctx.transport == "sse":
        return "Connected via SSE"
    elif ctx.transport == "streamable-http":
        return "Connected via Streamable HTTP"
    else:
        return "Transport unknown"
```

**Property signature:** `ctx.transport -> Literal["stdio", "sse", "streamable-http"] | None`

### MCP Request

```python
@mcp.tool
async def request_info(ctx: Context) -> dict:
    return {
        "request_id": ctx.request_id,
        "client_id": ctx.client_id or "Unknown client"
    }
```

**Available Properties:**

- `ctx.request_id -> str`: Unique ID for the current MCP request
- `ctx.client_id -> str | None`: ID of the client making the request
- `ctx.session_id -> str`: MCP session ID for session-based data sharing

#### Client Metadata (v2.13.1+)

Clients can send contextual information with their requests using the `meta` parameter, accessible through `ctx.request_context.meta`.
