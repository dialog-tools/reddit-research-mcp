"""Bounded structured runtime measurements; never captures request content."""
import asyncio
from contextlib import asynccontextmanager
import json
import logging
import time
import uuid

import psutil

logger = logging.getLogger("reddit_mcp.runtime")
logger.setLevel(logging.INFO)
if not logger.handlers:
    logger.addHandler(logging.StreamHandler())
logger.propagate = False


class RuntimeMetrics:
    def __init__(self):
        self.ready = False
        self.inflight_operations = 0
        self.started = time.monotonic()
        self.boot_id = uuid.uuid4().hex
        self._process = psutil.Process()

    def emit(self, event, **fields):
        logger.info(json.dumps({"event": event, "boot_id": self.boot_id, **fields}))

    def record_operation(self, operation, elapsed_seconds, outcome):
        self.emit("operation_complete", operation=operation,
                  elapsed_ms=round(elapsed_seconds * 1000, 2), outcome=outcome)

    @asynccontextmanager
    async def sampling(self, interval=60):
        async def sample():
            expected = time.monotonic()
            while True:
                now = time.monotonic()
                self.emit("runtime_sample", uptime_seconds=round(now-self.started, 2),
                          rss_bytes=self._process.memory_info().rss,
                          task_count=len(asyncio.all_tasks()),
                          inflight_operations=self.inflight_operations,
                          event_loop_lag_ms=round(max(0, now-expected)*1000, 2))
                expected = now + interval
                await asyncio.sleep(interval)
        self.emit("runtime_boot")
        task = asyncio.create_task(sample(), name="runtime-sampler")
        try:
            yield self
        finally:
            self.ready = False
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
            self.emit("runtime_shutdown")
