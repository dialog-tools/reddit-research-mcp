"""Bounded single-owner execution for synchronous upstream clients."""
import asyncio
from concurrent.futures import Future
import inspect
import queue
import threading
from contextvars import copy_context
from contextlib import asynccontextmanager


class WorkerBusy(RuntimeError):
    """The upstream worker has no available queue capacity."""


class BlockingWorker:
    def __init__(self, name: str, max_pending: int = 16):
        self._queue = asyncio.Queue(maxsize=max_pending)
        # One job in flight; the second slot is reserved for shutdown's sentinel.
        self._jobs = queue.Queue(maxsize=2)
        self._thread = threading.Thread(target=self._thread_main, name=name, daemon=True)
        self.cleanup = None
        self._pump = None
        self._closed = False

    async def __aenter__(self):
        self._thread.start()
        self._pump = asyncio.create_task(self._run(), name="upstream-worker")
        return self

    async def __aexit__(self, *exc):
        self._closed = True
        # Cancel queued work; the running network call retains its slot until
        # its own I/O timeout completes. Cancelling an await cannot kill a thread.
        while not self._queue.empty():
            item = self._queue.get_nowait()
            if item is not None and not item[1].done():
                item[1].set_exception(WorkerBusy("Server is draining"))
        self._queue.put_nowait(None)
        try:
            await asyncio.wait_for(asyncio.shield(self._pump), timeout=25)
        except TimeoutError:
            self._pump.cancel()
            await asyncio.gather(self._pump, return_exceptions=True)
        finally:
            self._jobs.put_nowait(None)
            await asyncio.to_thread(self._thread.join, 1)

    def _thread_main(self):
        try:
            while (item := self._jobs.get()) is not None:
                function, future = item
                if not future.set_running_or_notify_cancel():
                    continue
                try:
                    future.set_result(self._invoke(function))
                except BaseException as exc:
                    future.set_exception(exc)
        finally:
            if self.cleanup is not None:
                self.cleanup()

    async def call(self, function):
        if self._closed or self._pump is None:
            raise WorkerBusy("Server is draining")
        future = asyncio.get_running_loop().create_future()
        try:
            self._queue.put_nowait((function, future))
        except asyncio.QueueFull:
            raise WorkerBusy("Upstream busy; retry later") from None
        return await future

    @staticmethod
    def _invoke(function):
        result = function()
        if inspect.isawaitable(result):
            try:
                return asyncio.run(result)
            except asyncio.CancelledError:
                raise WorkerBusy("Request cancelled") from None
        return result

    async def _run(self):
        while (item := await self._queue.get()) is not None:
            function, future = item
            if future.cancelled():
                continue
            try:
                job = Future()
                self._jobs.put_nowait((function, job))
                result = await asyncio.wrap_future(job)
            except asyncio.CancelledError:
                if not future.done():
                    future.set_exception(WorkerBusy("Server is draining"))
                raise
            except Exception as exc:
                if not future.done():
                    future.set_exception(exc)
            else:
                if not future.done():
                    future.set_result(result)


class ProgressContext:
    """Await each progress notification on the request's event loop.

    Each worker can have only one outstanding notification; backpressure stays
    bounded. No FastMCP request context is used on the worker loop itself.
    """
    def __init__(self, context, loop):
        self._context = context
        self._loop = loop
        self._request_context = copy_context()

    async def report_progress(self, **kwargs):
        # FastMCP resolves request metadata through ContextVars, not fields on
        # Context. Restore the originating request context when scheduling.
        future = self._request_context.run(asyncio.run_coroutine_threadsafe,
            self._context.report_progress(**kwargs), self._loop)
        try:
            await asyncio.wait_for(asyncio.wrap_future(future), timeout=5)
        except (TimeoutError, asyncio.CancelledError):
            future.cancel()
            raise


@asynccontextmanager
async def upstream_workers():
    """Drain independent upstreams concurrently within one grace window."""
    reddit, chroma = BlockingWorker("reddit"), BlockingWorker("chroma")
    await reddit.__aenter__()
    await chroma.__aenter__()
    try:
        yield reddit, chroma
    finally:
        await asyncio.gather(reddit.__aexit__(None, None, None), chroma.__aexit__(None, None, None))
