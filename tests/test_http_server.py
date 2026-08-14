"""Tests for the HTTP entrypoint used by hosted deployments."""

from starlette.testclient import TestClient

from src.http_server import mcp


def make_client() -> TestClient:
    return TestClient(mcp.http_app())


def test_health_returns_ok_without_auth():
    with make_client() as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_mcp_endpoint_requires_auth():
    with make_client() as client:
        response = client.post(
            "/mcp",
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-06-18",
                    "capabilities": {},
                    "clientInfo": {"name": "test", "version": "0"},
                },
            },
            headers={"Accept": "application/json, text/event-stream"},
        )
    assert response.status_code == 401


def test_oauth_protected_resource_metadata_is_public():
    with make_client() as client:
        response = client.get("/.well-known/oauth-protected-resource/mcp")
    assert response.status_code == 200
    body = response.json()
    assert body["resource"].endswith("/mcp")
    assert body["authorization_servers"]
