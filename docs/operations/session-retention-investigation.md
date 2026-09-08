# Session retention investigation — September 8, 2026

## Causal reproducer

Production runtime inspection confirmed FastMCP 3.0.0 and MCP SDK 1.24.0.
The isolated loopback reproducer initialized 1,000 sessions in ten equal batches,
called a stub echo operation, explicitly deleted half, and abandoned half.
After every batch it waited the same test-only idle interval, collected Python
garbage, and measured retained transports, tasks, Python allocations, and RSS.
No live credentials or external services were used.

| After 1,000 sessions | Baseline | Candidate |
| --- | --- | --- |
| FastMCP | 3.0.0 | 3.0.0 |
| MCP SDK | 1.24.0 | 1.30.0 |
| SSE Starlette | 3.0.2 | 3.4.11 |
| Retained session transports | 1,000 | 0 |
| Tasks after cleanup | 1,503 | 4 |
| Traced Python allocations | 29,241,901 bytes | 1,937,180 bytes |
| Current RSS | 154,664,960 bytes | 93,519,872 bytes |
| Total elapsed | 52.36 seconds | 54.23 seconds |

The candidate's additional fourth task is the bounded SSE shutdown watcher.
The equal-work elapsed difference is approximately 3.6%; this small synthetic
comparison is not a production throughput benchmark. Raw observations and
allocation ownership are in `session-baseline.jsonl` and
`session-candidate.jsonl`; local user paths were normalized before publication.

The baseline session manager retained transports after DELETE. Abandoned
sessions also had no idle cleanup. Retained transport/task-group objects kept
Pydantic request/session models, async locks, memory streams, and associated
tasks alive. Tracemalloc growth accompanied RSS growth. The candidate releases
these owners and returns to bounded counts after every equal-work batch.
This demonstrates a concrete retention defect consistent with production's
growth; it does not prove that every byte of production growth has this cause.

An unlocked dependency install selected FastMCP 3.4.7 and failed both valid-token
HTTP tests: the custom verifier requires a JWT decode interface that version
removed. FastMCP is now explicitly pinned to 3.0.0. A clean install with that pin
and otherwise latest dependencies passed all 115 tests. This constraint change
did not change any resolved package/version/source in the Render lockfile.

MCP 1.29.1 was inspected and rejected as insufficient: explicit termination
still retained entries and idle cleanup did not protect active requests in the
required way. The [1.30.0 release](https://github.com/modelcontextprotocol/python-sdk/releases/tag/v1.30.0)
fixes DELETE/failure cleanup and supplies a 30-minute idle default, paused while
requests or GET streams are active. FastMCP remains on its existing major and
locked version. Only tests shorten SDK expiry; production uses its public default.

## Additional defects found by release checks

- A slow synchronous upstream blocked HTTP health checks on the baseline.
  Separate bounded owning workers now materialize upstream results off the
  event loop. The controlled test uses a ten-second upstream delay and requires
  all 20 concurrent health checks to finish within one second. Measured p95
  was 16.4 ms; all 20 finished in 21.7 ms. The identical ten-second test
  against the original application source took 9.93 seconds for those health
  checks and failed the one-second threshold.
- PRAW's owned requests session lacked reliable teardown. The new Reddit client
  owns/closes that session and applies finite socket timeouts. Quota exhaustion
  is checked at operation and per-request boundaries, including pagination.
- SSE 3.0.2 did not close an established GET stream on SIGTERM, causing the
  Uvicorn leaked-task timeout. SSE 3.4.11 closes the stream. Stream closure can
  end without a final HTTP chunk; clients must reconnect during deployment.
- FastMCP's outer HTTP lifespan survived beyond Uvicorn's signal scope, so a
  re-raised SIGTERM skipped owned-client cleanup. The Render entrypoint now
  serves the public `mcp.http_app()` through Uvicorn, keeping lifecycle ownership
  inside its shutdown sequence. Tests cover SIGTERM with both an open GET and
  an in-flight operation, one boot, one client close, and recorded cancellation.
- Worker progress initially lost FastMCP's request ContextVars. The bridge now
  restores the originating context when scheduling each notification on the
  request loop. Real HTTP tests verify delivery for all three async operations.
- `reddit://server-info` returned a dictionary that FastMCP 3.0 refused to
  serialize. It now returns the same document as JSON text at the same URI.

## Compatibility evidence

- Real HTTP verification accepts both supported Descope issuer formats and
  rejects expired, wrongly signed, wrong-issuer, and wrong-audience tokens.
- Claude Code's installed native client and Dialog's installed Agent SDK
  0.3.239 both connected and explicitly reconnected to a local authenticated
  candidate using synthetic credentials, without submitting a model prompt.
- Cursor CLI 2025.09.12 successfully listed the three tools over HTTP against
  the candidate's loopback transport fixture. That old CLI ignores configured
  HTTP headers, so this is transport coverage, not an end-to-end Cursor OAuth
  login test. Authentication is tested independently above; no user Cursor
  configuration or login state was changed.
- Both built-wheel console entrypoints passed: stdio initialized, listed the
  three tools, and read the JSON server-info resource; HTTP served health and
  both metadata paths and recorded lifespan shutdown after SIGTERM. All used
  synthetic settings.
- HTTP tests cover explicit DELETE, abandoned sessions, disconnected POSTs,
  active calls and GET streams, invalid initialization/session IDs, idle expiry,
  reinitialization, and configured canonical/legacy metadata identities.

## Long-running release gate

The final 512 MiB Linux container exercises the actual server, authentication
middleware, lifespan, workers, progress delivery, tool listing, and resource
reads. Only external Reddit/Chroma calls are stubbed. Every batch mixes explicit
DELETE with abandoned sessions, then measures sessions, tasks, threads, open
file descriptors, Python allocations, and RSS after cleanup.

The Python 3.11 and 3.12 GitHub matrix passed all 115 tests and package builds
([CI run](https://github.com/dialog-tools/reddit-research-mcp/actions/runs/34198364147)).
The two-hour result is pending. The exact FastMCP constraint was added after
the soak started; application source and every resolved runtime package remain
identical to the running container. Render's 60-second shutdown setting is a
platform rollout setting, not a change to the soak workload. Use `scripts/analyze_soak.py` on the completed
JSONL observations and independently check the container's exit/OOM status.
Earlier short exploratory soaks are not substitutes for this gate. Production
rollout and the seven-day stability window remain pending.
