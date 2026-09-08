import praw
import os
import logging
import requests
import time
from src.blocking_io import WorkerBusy
from pathlib import Path
from dotenv import load_dotenv


class BoundedSession(requests.Session):
    """Apply finite connect/read timeouts even when PRAW supplies its default."""
    def request(self, *args, **kwargs):
        timeout = kwargs.get("timeout") or 10
        kwargs["timeout"] = tuple(min(t or 10, 10) for t in timeout) if isinstance(timeout, tuple) else min(timeout, 10)
        return super().request(*args, **kwargs)


class OwnedReddit(praw.Reddit):
    def __init__(self, **kwargs):
        self.http_session = BoundedSession()
        try:
            super().__init__(requestor_kwargs={"session": self.http_session}, **kwargs)
        except Exception:
            self.http_session.close()
            raise

    def close(self):
        self.http_session.close()

    def request(self, *args, **kwargs):
        # Check each PRAW request, including pages fetched inside one operation.
        # This prevents the header-based limiter sleeping until an exhausted
        # quota resets. Normal pacing is still handled by PRAW (at most 10s).
        limits = self.auth.limits
        if limits.get("remaining") is not None and limits["remaining"] <= 0 and (limits.get("reset_timestamp") or 0) > time.time():
            raise WorkerBusy("Reddit rate limit exhausted; retry later")
        return super().request(*args, **kwargs)

    def __exit__(self, *_):
        self.close()


def enable_praw_debug_logging(level: int = logging.DEBUG):
    """
    Enable verbose PRAW logging for debugging Reddit API interactions.

    Args:
        level: Logging level (default: logging.DEBUG)

    Usage:
        from config import enable_praw_debug_logging
        enable_praw_debug_logging()  # Enable debug logging
        enable_praw_debug_logging(logging.INFO)  # Less verbose
    """
    for logger_name in ['prawcore', 'praw']:
        logger = logging.getLogger(logger_name)
        logger.setLevel(level)
        if not logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            ))
            logger.addHandler(handler)

def get_reddit_client() -> praw.Reddit:
    """Get configured Reddit client (read-only) from environment."""
    client_id = None
    client_secret = None
    user_agent = None
    
    # Method 1: Try environment variables
    client_id = os.environ.get("REDDIT_CLIENT_ID")
    client_secret = os.environ.get("REDDIT_CLIENT_SECRET")
    user_agent = os.environ.get("REDDIT_USER_AGENT", "RedditMCP/1.0")
    
    # Method 2: Try loading from .env file (local development)
    if not client_id or not client_secret:
        # Find .env file in project root
        env_path = Path(__file__).parent.parent / '.env'
        if env_path.exists():
            load_dotenv(env_path)
            client_id = os.getenv("REDDIT_CLIENT_ID")
            client_secret = os.getenv("REDDIT_CLIENT_SECRET")
            if not user_agent:
                user_agent = os.getenv("REDDIT_USER_AGENT", "RedditMCP/1.0")
    
    if not client_id or not client_secret:
        raise ValueError(
            "Reddit API credentials not found. Please set REDDIT_CLIENT_ID "
            "and REDDIT_CLIENT_SECRET either as OS environment variables or in a .env file"
        )
    
    # Create Reddit instance for read-only access
    reddit = OwnedReddit(
        client_id=client_id,
        client_secret=client_secret,
        user_agent=user_agent,
        redirect_uri="http://localhost:8080",  # Required even for read-only
        ratelimit_seconds=0,
        timeout=10,
        check_for_updates=False,
    )
    
    # Explicitly enable read-only mode
    reddit.read_only = True
    
    return reddit
