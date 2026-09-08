"""Loopback-only HTTP transport probe; no production credentials or upstreams."""

import asyncio
from contextlib import contextmanager
import gc
import inspect
import socket
import threading
import time
import os
from functools import partial
from unittest.mock import patch

from fastmcp import FastMCP
from starlette.responses import JSONResponse
import uvicorn
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager


def probe_app(idle_timeout=None):
    server = FastMCP("lifecycle-probe")

    @server.tool
    async def echo(value: str = "ok", delay: float = 0) -> str:
        await asyncio.sleep(delay)
        return value

    @server.resource("probe://info")
    def info() -> str:
        return "probe"

    options = {}
    if idle_timeout is not None and "session_idle_timeout" in inspect.signature(server.http_app).parameters:
        options["session_idle_timeout"] = idle_timeout
    if idle_timeout is not None and "session_idle_timeout" in inspect.signature(StreamableHTTPSessionManager).parameters:
        # Shorten the public SDK timeout only in this isolated probe. Production
        # uses SDK 1.30's supported 30-minute default through FastMCP 3.0.
        with patch("fastmcp.server.http.StreamableHTTPSessionManager",
                   partial(StreamableHTTPSessionManager, session_idle_timeout=idle_timeout)):
            app = server.http_app(**options)
    else:
        app = server.http_app(**options)
    manager = next(r.app.session_manager for r in app.routes if r.path == "/mcp")

    async def health(request):
        gc.collect()
        return JSONResponse({"status": "ok", "sessions": len(manager._server_instances),
                             "tasks": len(asyncio.all_tasks())})

    app.add_route("/health", health)
    return app


def production_probe_app(idle_timeout=.5):
    """Real server/worker/lifespan stack with synthetic auth and local upstreams."""
    from types import SimpleNamespace
    from fastmcp.server.auth.providers.jwt import StaticTokenVerifier
    for name, value in {"DESCOPE_PROJECT_ID":"Psoak", "SERVER_URL":"http://localhost:8000",
                        "REDDIT_CLIENT_ID":"soak", "REDDIT_CLIENT_SECRET":"soak",
                        "CHROMA_PROXY_API_KEY":"soak"}.items():
        os.environ[name] = value
    from src import server
    def client_factory():
        return SimpleNamespace(auth=SimpleNamespace(limits={"remaining":1000}),
                               close=lambda: None, __exit__=lambda *args: None)
    server.get_reddit_client = client_factory
    # Patch the external operation boundary; dispatch, workers, progress,
    # telemetry, HTTP sessions and the lifecycle remain real.
    def posts(**kwargs):
        time.sleep(.002)
        return {"posts":[], "count":0}
    async def discovery(**kwargs):
        time.sleep(.002)
        await kwargs["ctx"].report_progress(progress=1, total=1)
        return {"subreddits":[], "summary":{"total_found":0}}
    server.fetch_subreddit_posts = posts
    server.discover_subreddits = discovery
    server.mcp.auth = StaticTokenVerifier(tokens={"soak-token":{"client_id":"soak", "scopes":[]}})
    with patch("fastmcp.server.http.StreamableHTTPSessionManager",
               partial(StreamableHTTPSessionManager, session_idle_timeout=idle_timeout)):
        app = server.mcp.http_app()
    endpoint = next(r.app for r in app.routes if r.path == "/mcp")
    while not hasattr(endpoint, "session_manager"):
        endpoint = endpoint.app
    manager = endpoint.session_manager
    async def sample(request):
        import psutil
        gc.collect()
        return JSONResponse({"status":"ok", "sessions":len(manager._server_instances),
                             "tasks":len(asyncio.all_tasks()), "threads":threading.active_count(),
                             "file_descriptors":psutil.Process().num_fds()})
    app.add_route("/probe", sample)
    return app


@contextmanager
def live_server(app):
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(app, log_level="error", ws="none", timeout_graceful_shutdown=2))
    thread = threading.Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True)
    thread.start()
    deadline = time.monotonic() + 10
    while not server.started:
        if not thread.is_alive() or time.monotonic() > deadline:
            raise RuntimeError("Probe server did not start")
        time.sleep(.01)
    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        server.should_exit = True
        thread.join(10)
        sock.close()
        assert not thread.is_alive(), "Probe server did not stop"


ACCEPT = {"Accept": "application/json, text/event-stream"}


def initialize(client):
    response = client.post("/mcp", headers=ACCEPT, json={
        "jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
            "protocolVersion": "2025-06-18", "capabilities": {},
            "clientInfo": {"name": "reliability-probe", "version": "1"}}})
    response.raise_for_status()
    headers = {**ACCEPT, "mcp-session-id": response.headers["mcp-session-id"]}
    client.post("/mcp", headers=headers, json={
        "jsonrpc": "2.0", "method": "notifications/initialized"}).raise_for_status()
    return headers
