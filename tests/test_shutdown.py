import asyncio
import signal
import socket
import subprocess
import sys
import time

import httpx
import pytest

from tests.http_support import initialize


@pytest.mark.parametrize("active", [False, True])
async def test_sigterm_closes_live_get_stream_without_leaked_tasks(tmp_path, active):
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    log_path = tmp_path / "shutdown.log"
    with log_path.open("w") as log:
        process = subprocess.Popen([sys.executable, "-m", "tests.shutdown_probe", str(port)]+(["active"] if active else []),
                                   stdout=log, stderr=log)
        try:
            with httpx.Client(base_url=f"http://127.0.0.1:{port}",
                              headers={"Authorization":"Bearer soak-token"}) as setup:
                deadline = time.monotonic()+10
                while True:
                    try:
                        if setup.get("/health").status_code == 200:
                            break
                    except httpx.ConnectError:
                        pass
                    assert time.monotonic() < deadline, log_path.read_text()
                    await asyncio.sleep(.05)
                headers = initialize(setup)
            async with httpx.AsyncClient(base_url=f"http://127.0.0.1:{port}",
                    headers={"Authorization":"Bearer soak-token"}, timeout=8) as client:
                work = None
                if active:
                    work = asyncio.create_task(client.post("/mcp", headers=headers, json={
                        "jsonrpc":"2.0","id":2,"method":"tools/call",
                        "params":{"name":"execute_operation","arguments":{
                            "operation_id":"fetch_posts","parameters":{}}}}))
                    deadline = time.monotonic()+5
                    while "PROBE_OPERATION_STARTED" not in log_path.read_text():
                        assert time.monotonic() < deadline
                        await asyncio.sleep(.02)
                async with client.stream("GET", "/mcp", headers=headers) as stream:
                    assert stream.status_code == 200
                    process.send_signal(signal.SIGTERM)
                    # SSE auto-drain ends the stream during deployment. Clients
                    # must reconnect; Uvicorn may close without a final chunk.
                    try:
                        async for _ in stream.aiter_bytes():
                            pass
                    except httpx.RemoteProtocolError:
                        pass
                if work:
                    await asyncio.gather(work, return_exceptions=True)
            await asyncio.to_thread(process.wait, 8)
            assert process.returncode in (0, -signal.SIGTERM)
        finally:
            if process.poll() is None:
                process.kill()
                process.wait()
    output = log_path.read_text()
    assert "timeout graceful shutdown exceeded" not in output
    assert "Task was destroyed" not in output
    assert '"event": "runtime_shutdown"' in output
    assert output.count('"event": "runtime_boot"') == 1
    assert output.count("PROBE_REDDIT_CLOSED") == 1
    if active:
        assert '"outcome": "cancelled"' in output or '"outcome": "success"' in output
