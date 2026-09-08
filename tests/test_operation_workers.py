import threading

import httpx
import pytest
from fastmcp.server.auth.providers.jwt import StaticTokenVerifier

from scripts.soak_http import require_rpc_success
from tests.http_support import initialize, live_server


@pytest.mark.parametrize("operation,function,owner", [
    ("fetch_posts","fetch_subreddit_posts","reddit"),
    ("search_subreddit","search_in_subreddit","reddit"),
    ("fetch_multiple","fetch_multiple_subreddits","reddit"),
    ("fetch_comments","fetch_submission_with_comments","reddit"),
    ("discover_subreddits","discover_subreddits","chroma"),
])
def test_all_blocking_operations_execute_on_their_owner_and_preserve_progress(monkeypatch,operation,function,owner):
    from src import server
    observed = []
    async def async_operation(**kwargs):
        observed.append(threading.current_thread().name)
        await kwargs["ctx"].report_progress(progress=1, total=1)
        return {"done":True}
    def sync_operation(**kwargs):
        observed.append(threading.current_thread().name)
        return {"done":True}
    is_async = operation in {"fetch_multiple","fetch_comments","discover_subreddits"}
    monkeypatch.setattr(server,function,async_operation if is_async else sync_operation)
    monkeypatch.setattr(server.mcp,"auth",StaticTokenVerifier(tokens={"test":{"client_id":"test","scopes":[]}}))
    with live_server(server.mcp.http_app()) as url, httpx.Client(base_url=url,
            headers={"Authorization":"Bearer test"}) as client:
        headers = initialize(client)
        response = client.post("/mcp",headers=headers,json={"jsonrpc":"2.0","id":2,"method":"tools/call",
            "params":{"name":"execute_operation","arguments":{"operation_id":operation,"parameters":{}},
                      "_meta":{"progressToken":"progress-test"}}})
        require_rpc_success(response)
        assert observed == [owner]
        if is_async:
            assert 'notifications/progress' in response.text
            assert 'progress-test' in response.text
        client.delete("/mcp",headers=headers).raise_for_status()
