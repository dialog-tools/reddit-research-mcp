import asyncio
import time

import httpx
from fastmcp.server.auth.providers.jwt import StaticTokenVerifier

from tests.http_support import ACCEPT, initialize, live_server


async def test_health_remains_responsive_during_slow_reddit_request(monkeypatch):
    from src import server
    def slow_posts(**kwargs):
        time.sleep(10)
        return {"posts": [], "count": 0}
    monkeypatch.setattr(server, "fetch_subreddit_posts", slow_posts)
    monkeypatch.setattr(server.mcp, "auth", StaticTokenVerifier(
        tokens={"test-token": {"client_id": "test", "scopes": []}}))
    with live_server(server.mcp.http_app()) as url:
        with httpx.Client(base_url=url, headers={"Authorization": "Bearer test-token"}) as setup:
            headers = initialize(setup)
        async with httpx.AsyncClient(base_url=url, headers={"Authorization": "Bearer test-token"}, timeout=15) as client:
            request = asyncio.create_task(client.post("/mcp", headers=headers, json={
                "jsonrpc": "2.0", "id": 2, "method": "tools/call",
                "params": {"name": "execute_operation", "arguments": {
                    "operation_id": "fetch_posts", "parameters": {"subreddit_name": "test"}}}}))
            await asyncio.sleep(.1)
            started = time.monotonic()
            responses = await asyncio.gather(*(client.get("/health") for _ in range(20)))
            duration = time.monotonic() - started
            result = await request
            assert result.status_code == 200
            assert all(r.status_code == 200 for r in responses)
            assert duration < 1
            p95 = sorted(r.elapsed.total_seconds() for r in responses)[18]
            print(f"Controlled health check: p95={p95*1000:.1f}ms, all20={duration*1000:.1f}ms during 10s upstream stall")
            await client.delete("/mcp", headers=headers)
