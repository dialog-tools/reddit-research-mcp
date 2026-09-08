import asyncio
import json
import logging
import pytest


@pytest.fixture(autouse=True)
def capture_runtime(caplog):
    from src.observability import logger
    logger.addHandler(caplog.handler)
    yield
    logger.removeHandler(caplog.handler)


async def test_sampler_stops_at_lifespan_end_and_reports_current_resources(caplog):
    from src.observability import RuntimeMetrics
    metrics = RuntimeMetrics()
    with caplog.at_level(logging.INFO, logger="reddit_mcp.runtime"):
        async with metrics.sampling(interval=.02):
            metrics.inflight_operations = 2
            await asyncio.sleep(.06)
        count = len(caplog.records)
        await asyncio.sleep(.04)
    assert len(caplog.records) == count
    samples = [json.loads(r.message) for r in caplog.records if '"runtime_sample"' in r.message]
    assert samples
    assert samples[-1]["inflight_operations"] == 2
    assert samples[-1]["rss_bytes"] > 0
    assert samples[-1]["event_loop_lag_ms"] >= 0
    assert set(samples[-1]) == {"event", "boot_id", "uptime_seconds", "rss_bytes",
                               "task_count", "inflight_operations", "event_loop_lag_ms"}


def test_operation_outcomes_do_not_include_input_or_exception_text(caplog):
    from src.observability import RuntimeMetrics
    metrics = RuntimeMetrics()
    with caplog.at_level(logging.INFO, logger="reddit_mcp.runtime"):
        metrics.record_operation("fetch_posts", 1.5, "upstream_timeout")
    assert json.loads(caplog.records[-1].message)["outcome"] == "upstream_timeout"


def test_health_is_unavailable_when_initialization_failed(monkeypatch):
    from src import server
    from starlette.testclient import TestClient
    def unavailable():
        raise ValueError("missing credentials")
    monkeypatch.setattr(server, "get_reddit_client", unavailable)
    with TestClient(server.mcp.http_app()) as client:
        assert client.get("/health").status_code == 503
