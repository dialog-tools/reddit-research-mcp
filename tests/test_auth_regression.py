import pytest
from authlib.jose import JsonWebKey
from fastmcp.server.auth.providers.jwt import RSAKeyPair
from starlette.testclient import TestClient
from tests.http_support import ACCEPT


@pytest.mark.parametrize("issuer,audience,expired,wrong_key,expected", [
    ("Ptest-reliability", None, False, False, 200),
    ("https://api.descope.com/v1/apps/Ptest-reliability", "Ptest-reliability", False, False, 200),
    ("unexpected", "Ptest-reliability", False, False, 401),
    ("Ptest-reliability", None, True, False, 401),
    ("Ptest-reliability", None, False, True, 401),
    ("Ptest-reliability", "incorrect", False, False, 401),
])
def test_real_http_auth_preserves_both_issuer_formats(monkeypatch, issuer, audience, expired, wrong_key, expected):
    from src import server
    key = RSAKeyPair.generate()
    async def local_key(token):
        return JsonWebKey.import_key(key.public_key)
    monkeypatch.setattr(server.multi_issuer_verifier, "_get_verification_key", local_key)
    token = (RSAKeyPair.generate() if wrong_key else key).create_token(
        issuer=issuer, audience=audience, expires_in_seconds=-60 if expired else 60)
    with TestClient(server.mcp.http_app()) as client:
        response = client.post("/mcp", headers={**ACCEPT, "Authorization": "Bearer "+token}, json={
            "jsonrpc":"2.0", "id":1, "method":"initialize", "params":{
                "protocolVersion":"2025-06-18", "capabilities":{},
                "clientInfo":{"name":"auth-regression", "version":"1"}}})
        assert response.status_code == expected
