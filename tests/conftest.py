"""Synthetic configuration: project tests never load live .env credentials."""
import os

for key, value in {
    "DESCOPE_PROJECT_ID": "Ptest-reliability",
    "REDDIT_CLIENT_ID": "test-client",
    "REDDIT_CLIENT_SECRET": "test-secret",
    "CHROMA_PROXY_API_KEY": "test-key",
    "SERVER_URL": "http://localhost:8000",
}.items():
    os.environ[key] = value
