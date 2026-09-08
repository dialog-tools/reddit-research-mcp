import asyncio
import threading

import pytest


async def test_slow_call_does_not_block_event_loop_and_preserves_thread_ownership():
    from src.blocking_io import BlockingWorker
    gate = threading.Event()
    async with BlockingWorker("probe") as worker:
        task = asyncio.create_task(worker.call(lambda: (gate.wait(2), threading.get_ident())[1]))
        await asyncio.sleep(.05)
        assert not task.done()
        gate.set()
        thread = await task
        assert thread != threading.get_ident()
        assert await worker.call(threading.get_ident) == thread


async def test_queue_is_bounded_even_after_running_request_is_cancelled():
    from src.blocking_io import BlockingWorker, WorkerBusy
    started, release = threading.Event(), threading.Event()
    def slow():
        started.set()
        release.wait(2)
    async with BlockingWorker("probe", max_pending=1) as worker:
        first = asyncio.create_task(worker.call(slow))
        while not started.is_set():
            await asyncio.sleep(.001)
        first.cancel()
        with pytest.raises(asyncio.CancelledError):
            await first
        queued = asyncio.create_task(worker.call(lambda: "second"))
        await asyncio.sleep(.01)
        try:
            with pytest.raises(WorkerBusy):
                await worker.call(lambda: "must not start")
            assert not queued.done()
        finally:
            release.set()
        assert await queued == "second"


async def test_worker_propagates_errors_and_can_continue():
    from src.blocking_io import BlockingWorker
    async with BlockingWorker("probe") as worker:
        with pytest.raises(ValueError, match="bad input"):
            await worker.call(lambda: (_ for _ in ()).throw(ValueError("bad input")))
        assert await worker.call(lambda: 3) == 3


async def test_progress_runs_on_request_loop_in_order():
    from src.blocking_io import BlockingWorker, ProgressContext
    loop = asyncio.get_running_loop()
    events = []
    class Context:
        async def report_progress(self, **kwargs):
            assert asyncio.get_running_loop() is loop
            events.append(kwargs["progress"])
    bridge = ProgressContext(Context(), loop)
    async def work():
        await bridge.report_progress(progress=1)
        await bridge.report_progress(progress=2)
        return "done"
    async with BlockingWorker("probe") as worker:
        assert await worker.call(work) == "done"
    assert events == [1, 2]
