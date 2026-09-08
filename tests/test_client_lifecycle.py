import threading


async def test_owned_client_cleanup_runs_on_owner_thread():
    from src.blocking_io import BlockingWorker
    closed = []
    async with BlockingWorker("owner") as worker:
        owner = await worker.call(threading.get_ident)
        worker.cleanup = lambda: closed.append(threading.get_ident())
    assert closed == [owner]


def test_reddit_client_closes_owned_http_session(monkeypatch):
    from src.config import get_reddit_client
    client = get_reddit_client()
    assert hasattr(client, "http_session")
    closed = []
    monkeypatch.setattr(client.http_session, "close", lambda: closed.append(True))
    client.close()
    assert closed == [True]
