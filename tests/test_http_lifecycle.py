"""Guard against transport/session retention in the locked HTTP stack."""
import time
import asyncio

import httpx

from tests.http_support import initialize, live_server, probe_app


def test_deleted_sessions_release_retained_transports():
    with live_server(probe_app()) as url, httpx.Client(base_url=url) as client:
        for _ in range(10):
            headers = initialize(client)
            client.delete("/mcp", headers=headers).raise_for_status()
        time.sleep(.1)
        assert client.get("/health").json()["sessions"] == 0


def test_abandoned_sessions_expire_without_client_delete():
    with live_server(probe_app(idle_timeout=.15)) as url, httpx.Client(base_url=url) as client:
        initialize(client)
        time.sleep(.4)
        assert client.get("/health").json()["sessions"] == 0


def test_active_operation_is_not_expired_mid_request():
    with live_server(probe_app(idle_timeout=.15)) as url, httpx.Client(base_url=url) as client:
        headers = initialize(client)
        result = client.post("/mcp", headers=headers, json={
            "jsonrpc":"2.0", "id":2, "method":"tools/call",
            "params":{"name":"echo", "arguments":{"value":"completed", "delay":.4}}})
        assert result.status_code == 200
        assert "completed" in result.text
        time.sleep(.3)
        assert client.get("/health").json()["sessions"] == 0


async def test_open_get_stream_survives_and_expires_after_disconnect():
    with live_server(probe_app(idle_timeout=.15)) as url:
        with httpx.Client(base_url=url) as setup:
            headers = initialize(setup)
        async with httpx.AsyncClient(base_url=url) as client:
            async with client.stream("GET", "/mcp", headers=headers) as stream:
                assert stream.status_code == 200
                await asyncio.sleep(.4)
                assert (await client.get("/health")).json()["sessions"] == 1
            await asyncio.sleep(.4)
            assert (await client.get("/health")).json()["sessions"] == 0


def test_invalid_opening_request_does_not_retain_session():
    from tests.http_support import ACCEPT
    with live_server(probe_app()) as url, httpx.Client(base_url=url) as client:
        for _ in range(10):
            response = client.post("/mcp", headers=ACCEPT, json={"jsonrpc":"2.0", "id":1, "method":"tools/list"})
            assert response.status_code >= 400
        assert client.get("/health").json()["sessions"] == 0


async def test_disconnected_post_releases_session_after_idle_expiry():
    with live_server(probe_app(idle_timeout=.15)) as url:
        with httpx.Client(base_url=url) as setup:
            headers = initialize(setup)
        async with httpx.AsyncClient(base_url=url) as client:
            async with client.stream("POST", "/mcp", headers=headers, json={
                "jsonrpc":"2.0", "id":2, "method":"tools/call",
                "params":{"name":"echo", "arguments":{"delay":10}}}) as stream:
                assert stream.status_code == 200
            await asyncio.sleep(.5)
            assert (await client.get("/health")).json()["sessions"] == 0


def test_client_can_reinitialize_after_session_expiry():
    from tests.http_support import ACCEPT
    with live_server(probe_app(idle_timeout=.15)) as url, httpx.Client(base_url=url) as client:
        old = initialize(client)
        time.sleep(.3)
        request = {"jsonrpc":"2.0", "id":2, "method":"tools/list"}
        assert client.post("/mcp",headers=old,json=request).status_code == 404
        assert client.post("/mcp",headers={**ACCEPT,"mcp-session-id":"unknown"},json=request).status_code == 404
        new = initialize(client)
        assert new["mcp-session-id"] != old["mcp-session-id"]
        assert client.post("/mcp",headers=new,json=request).status_code == 200
        client.delete("/mcp",headers=new).raise_for_status()
