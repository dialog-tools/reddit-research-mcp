"""Repeatable loopback-only session churn; emits JSON observations to stdout."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import time
import tracemalloc

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import httpx
from tests.http_support import initialize, live_server, probe_app, production_probe_app


def require_rpc_success(response):
    response.raise_for_status()
    messages = ([response.json()] if "application/json" in response.headers.get("content-type", "")
                else [json.loads(line[5:].strip()) for line in response.text.splitlines() if line.startswith("data:")])
    replies = [message for message in messages if "id" in message]
    if not replies:
        raise RuntimeError("Missing RPC response")
    for message in replies:
        result = message.get("result", {})
        structured = result.get("structuredContent", {})
        if "error" in message or result.get("isError") or structured.get("success") is False:
            raise RuntimeError("RPC or tool returned an error")
        for content in result.get("content", []):
            if content.get("type") == "text":
                try:
                    data = json.loads(content["text"])
                except (ValueError, KeyError):
                    continue
                if isinstance(data, dict) and data.get("success") is False:
                    raise RuntimeError("Tool returned an application error")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--batches", type=int, default=10)
    parser.add_argument("--sessions", type=int, default=100)
    parser.add_argument("--seconds", type=float, default=0)
    parser.add_argument("--idle-timeout", type=float, default=.5)
    parser.add_argument("--production-stack", action="store_true")
    args = parser.parse_args()
    tracemalloc.start(5)
    start = time.monotonic()
    app = production_probe_app(args.idle_timeout) if args.production_stack else probe_app(args.idle_timeout)
    with live_server(app) as url, httpx.Client(base_url=url, timeout=10,
            headers={"Authorization":"Bearer soak-token"} if args.production_stack else {}) as client:
        batch = 0
        while batch < args.batches or time.monotonic() - start < args.seconds:
            for i in range(args.sessions):
                headers = initialize(client)
                params = ({"name":"execute_operation", "arguments":{
                    "operation_id":"fetch_posts" if i % 2 == 0 else "discover_subreddits",
                    "parameters":{"subreddit_name":"probe"} if i % 2 == 0 else {"query":"probe"}}}
                    if args.production_stack else {"name":"echo", "arguments":{"value":"probe"}})
                if args.production_stack:
                    params["_meta"] = {"progressToken":"soak-progress"}
                response = client.post("/mcp", headers=headers, json={
                    "jsonrpc": "2.0", "id": 2, "method": "tools/call",
                    "params": params})
                require_rpc_success(response)
                if args.production_stack and i % 2:
                    if "notifications/progress" not in response.text:
                        raise RuntimeError("Progress notification missing")
                if args.production_stack:
                    for request_id, method, params in [(3,"tools/list",{}),
                            (4,"resources/read",{"uri":"reddit://server-info"})]:
                        require_rpc_success(client.post("/mcp", headers=headers, json={
                            "jsonrpc":"2.0", "id":request_id, "method":method,"params":params}))
                if i % 2 == 0:
                    client.delete("/mcp", headers=headers).raise_for_status()
            time.sleep(args.idle_timeout + .2)
            health = client.get("/probe" if args.production_stack else "/health").json()
            current, peak = tracemalloc.get_traced_memory()
            if sys.platform == "linux":
                rss = int(Path("/proc/self/statm").read_text().split()[1]) * 4096
            else:
                import os
                rss = int(subprocess.check_output(["ps", "-o", "rss=", "-p", str(os.getpid())])) * 1024
            print(json.dumps({"batch": batch, "elapsed": round(time.monotonic()-start, 2),
                              **health, "python_bytes": current, "python_peak": peak, "rss_bytes": rss}), flush=True)
            batch += 1
        print(json.dumps({"allocations": [str(s) for s in tracemalloc.take_snapshot().statistics("lineno")[:15]]}), flush=True)


if __name__ == "__main__":
    main()
