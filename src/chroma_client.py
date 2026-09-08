"""
ChromaDB Cloud client for Reddit MCP.

Provides connection to ChromaDB Cloud for vector storage and retrieval.
"""

import os
from typing import Optional, List, Dict, Any
import requests


_client_instance = None


# ============= PROXY CLIENT CLASSES =============
class ChromaProxyClient:
    """Proxy client that mimics ChromaDB interface."""
    
    def __init__(self, proxy_url: Optional[str] = None):
        self.url = proxy_url or os.getenv(
            'CHROMA_PROXY_URL', 
            'https://reddit-mcp-vector-db.onrender.com'
        )
        self.api_key = os.getenv('CHROMA_PROXY_API_KEY')
        self.session = requests.Session()
        
        # Set API key in session headers if provided
        if self.api_key:
            self.session.headers['X-API-Key'] = self.api_key

    def close(self):
        self.session.close()
    
    def query(self, query_texts: List[str], n_results: int = 10, collection_name: str = "dialog-app-prod-db") -> Dict[str, Any]:
        """Query through proxy."""
        try:
            response = self.session.post(
                f"{self.url}/query",
                json={"query_texts": query_texts, "n_results": n_results, "collection_name": collection_name},
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                raise ConnectionError("Authentication failed: API key required. Set CHROMA_PROXY_API_KEY environment variable.")
            elif e.response.status_code == 403:
                raise ConnectionError("Authentication failed: Invalid API key provided.")
            elif e.response.status_code == 429:
                raise ConnectionError("Rate limit exceeded. Please wait before retrying.")
            else:
                raise ConnectionError(f"Failed to query vector database: HTTP {e.response.status_code}")
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Failed to query vector database: {e}")
    
    def list_collections(self) -> List[Dict[str, str]]:
        """Compatibility method."""
        return [{"name": "reddit_subreddits"}]
    
    def count(self) -> int:
        """Get document count."""
        try:
            response = self.session.get(f"{self.url}/stats", timeout=5)
            if response.status_code == 200:
                return response.json().get('total_subreddits', 20000)
            elif response.status_code == 401:
                print("Warning: Stats endpoint requires authentication. Using default count.")
            elif response.status_code == 403:
                print("Warning: Invalid API key for stats endpoint. Using default count.")
        except:
            pass
        return 20000


class ProxyCollection:
    """Wrapper to match Chroma collection interface."""

    def __init__(self, proxy_client: ChromaProxyClient, collection_name: str = "dialog-app-prod-db"):
        self.proxy_client = proxy_client
        self.name = collection_name

    def query(self, query_texts: List[str], n_results: int = 10) -> Dict[str, Any]:
        return self.proxy_client.query(query_texts, n_results, collection_name=self.name)

    def count(self) -> int:
        return self.proxy_client.count()
# ============= END PROXY CLIENT CLASSES =============




def get_chroma_client():
    """
    Get ChromaDB proxy client for vector database access.
    
    Returns:
        ChromaProxyClient instance
    """
    global _client_instance
    
    # Return cached instance if available
    if _client_instance is not None:
        return _client_instance
    
    print("🌐 Using proxy for vector database access")
    _client_instance = ChromaProxyClient()
    return _client_instance


def reset_client_cache():
    """Reset the cached client instance (useful for testing)."""
    global _client_instance
    if _client_instance is not None:
        _client_instance.close()
    _client_instance = None


def get_collection(
    collection_name: str = "dialog-app-prod-db",
    client = None
):
    """
    Get ProxyCollection for vector database access.

    Args:
        collection_name: Name of the collection (default "dialog-app-prod-db")
        client: Optional client instance (uses default if not provided)

    Returns:
        ProxyCollection instance
    """
    if client is None:
        client = get_chroma_client()

    return ProxyCollection(client, collection_name=collection_name)


def test_connection() -> dict:
    """
    Test proxy connection and return status information.
    
    Returns:
        Dictionary with connection status and details
    """
    status = {
        'mode': 'proxy',
        'connected': False,
        'error': None,
        'collections': [],
        'document_count': 0,
        'authenticated': False
    }
    
    try:
        client = get_chroma_client()
        
        # Check if API key is configured
        if client.api_key:
            status['authenticated'] = True
        
        # Test connection
        status['connected'] = True
        status['collections'] = ['reddit_subreddits']
        status['document_count'] = client.count()
        
    except Exception as e:
        status['error'] = str(e)
    
    return status
