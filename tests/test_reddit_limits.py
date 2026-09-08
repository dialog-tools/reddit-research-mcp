import time
from unittest.mock import PropertyMock

import praw
import pytest
import requests

from src.blocking_io import WorkerBusy
from src.config import BoundedSession, get_reddit_client


def test_exhausted_quota_is_rejected_before_next_page_can_sleep(monkeypatch):
    client = get_reddit_client()
    limits = {"remaining": 1, "reset_timestamp": time.time()+600}
    monkeypatch.setattr(type(client.auth), "limits", PropertyMock(return_value=limits))
    calls = []
    def request(*args, **kwargs):
        calls.append(True)
        limits["remaining"] = 0
        return {"page": 1}
    monkeypatch.setattr(praw.Reddit, "request", request)
    try:
        assert client.request("GET", "/page1") == {"page": 1}
        with pytest.raises(WorkerBusy, match="rate limit"):
            client.request("GET", "/page2")
        assert calls == [True]
        assert client.config.ratelimit_seconds == 0
    finally:
        client.close()


@pytest.mark.parametrize("supplied,expected", [(None,10),(16,10),((2,30),(2,10)),((None,None),(10,10))])
def test_reddit_socket_timeouts_are_finite(monkeypatch,supplied,expected):
    observed = []
    def request(*args,**kwargs):
        observed.append(kwargs["timeout"])
    monkeypatch.setattr(requests.Session,"request",request)
    with BoundedSession() as client:
        client.get("https://example.invalid", timeout=supplied)
    assert observed == [expected]
