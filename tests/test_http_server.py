"""Tests for the HTTP entrypoint used by hosted deployments."""

from starlette.testclient import TestClient
import pytest

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


@pytest.mark.parametrize("path", ["/.well-known/oauth-protected-resource/mcp", "/.well-known/oauth-protected-resource"])
def test_oauth_protected_resource_metadata_is_public(path):
    with make_client() as client:
        response = client.get(path)
    assert response.status_code == 200
    body = response.json()
    assert body["resource"].endswith("/mcp")
    assert body["authorization_servers"]


@pytest.mark.parametrize("origin", ["http://localhost:8000", "https://mcp.dialog.tools/", "https://reddit-research-mcp.fastmcp.app"])
def test_metadata_aliases_share_configured_host_identity(monkeypatch, origin):
    from src import server
    from fastmcp.server.auth.providers.descope import DescopeProvider
    monkeypatch.setenv("SERVER_URL", origin)
    # Auth metadata is constructed once at process startup from SERVER_URL.
    monkeypatch.setattr(mcp, "auth", DescopeProvider(project_id="Ptest-reliability",
        base_url=origin, descope_base_url="https://api.descope.com", token_verifier=server.multi_issuer_verifier))
    with make_client() as client:
        fallback = client.get("/.well-known/oauth-protected-resource").json()
        advertised = client.get("/.well-known/oauth-protected-resource/mcp").json()
    assert fallback == advertised
    assert fallback["resource"] == origin.rstrip("/")+"/mcp"
