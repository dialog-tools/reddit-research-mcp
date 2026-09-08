"""Subprocess fixture for real SIGTERM tests; synthetic auth/upstreams only."""
import sys
import os
import time
from tests.http_support import production_probe_app

if __name__ == "__main__":
    production_probe_app()
    from src import server, http_server
    factory = server.get_reddit_client
    def owned_client():
        client = factory()
        client.__exit__ = lambda *args: print("PROBE_REDDIT_CLOSED", flush=True)
        return client
    server.get_reddit_client = owned_client
    if len(sys.argv) > 2:
        def slow_posts(**kwargs):
            print("PROBE_OPERATION_STARTED", flush=True)
            time.sleep(2)
            return {"posts":[], "count":0}
        server.fetch_subreddit_posts = slow_posts
    os.environ["PORT"] = sys.argv[1]
    os.environ["HOST"] = "127.0.0.1"
    http_server.main()
