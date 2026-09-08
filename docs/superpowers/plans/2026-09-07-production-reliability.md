# Production MCP Reliability Implementation Plan

> **For agentic workers:** Use `superpowers:executing-plans` to implement this plan task by task after approval. Execute inline; delegate only if separately authorized. Checkboxes track execution, not approval.

**Status:** Approved by Chris ("ok proceed - approved"). Implementation is on `fix/mcp-production-reliability`; release gates and rollout are in progress. See `docs/operations/production-reliability.md` for operational status.

**Goal:** Eliminate unbounded memory growth, keep the HTTP server responsive during upstream calls, and make production degradation visible before clients experience an outage.

**Architecture:** Preserve the authenticated, stateful Streamable HTTP interface and the existing single Render instance. Establish a repeatable session-lifecycle test, adopt a verified cleanup fix, isolate blocking upstream work, and add lightweight diagnostics plus scheduled production checks. Keep dependency-health monitoring separate from Render's frequent process-health probe.

**Tech stack:** Python 3.12 in production, FastMCP, MCP Python SDK, PRAW, requests/httpx, uv, pytest, Render, GitHub Actions for pull-request tests.

**Spec:** The design, decision rules, operational thresholds, and acceptance criteria in this document are the specification for this remediation.

## Approval scope and constraints

- Approval of the complete plan authorizes creating and switching to `fix/mcp-production-reliability`, local implementation and tests, creating a PR, merging after the gates below pass, the resulting production deployment, provisioning the monitoring cron job, and rollback if a gate fails. The authorized branch has been created.
- Monitoring budget: up to $5/month incremental, including one smallest-plan Render cron job. Existing MCP and vector database compute plans remain as configured. Verify pricing before provisioning; any larger cost requires a revised proposal.
- Notifications go to Chris through the existing Render account email destination. Approval includes configuring these alerts and sending a labeled test alert. Do not add Slack recipients or other people.
- A temporary preventive redeploy is authorized only if refreshed memory stays at or above 85% for 10 minutes and the tested fix is not ready. Capture evidence first, use the current known-good code, verify client reconnection, and report the event. This is operator-executed mitigation, not a scheduled restart loop.
- Keep the canonical endpoint `https://mcp.dialog.tools/mcp`, both accepted Descope issuer formats, operation schemas, resource URIs, and progress notifications compatible.
- Keep local stdio clients working. The legacy FastMCP-hosted deployment also follows `main`; verify its host-specific resource identity and compatibility when shared code changes.
- Use synthetic credentials and mocked upstream services for automated load tests. Production smoke tests are small, authenticated, read-only calls.
- Do not log tokens, request bodies, feed contents, or user identifiers in new diagnostic output. Do not publish a release tag to PyPI or the MCP Registry as part of this hosted-service repair.
- The pending AgentWatch items belong to a separate local configuration review and are outside this production remediation.

## Evidence and important uncertainties

The production audit covered August 30 through September 8, 2026, 04:46 UTC (September 7, 21:46 Pacific).

| Finding | Evidence | Interpretation |
| --- | --- | --- |
| Service works now | Public health returned 200 in approximately 0.3 seconds; authenticated discovery and Reddit fetching succeeded | Useful point-in-time checks, not proof of long-term stability |
| Continuing memory growth | Current instance grew from 103.7 MiB to 296.7 MiB over 77 hours; latest minute sample was approximately 300.4 MiB of 512 MiB | Approximately 60 MiB/day; linear extrapolation reaches the cap around September 11, subject to traffic and runtime changes |
| August 31 interruption | Memory reached 511.8 MiB; process restarted at 10:08:28 UTC; 118 request-log 502s between 10:08:18 and 10:08:44 UTC | Confirmed by Render event `evt-daal54tbedkc73cc6gmg`: `oomKilled`, memory limit `512Mi` |
| September 4 replacement | Render-triggered deployment of the same commit; old process timed out with 31 running tasks | Replacement and incomplete shutdown are confirmed; memory exhaustion as the reason for this particular deployment is not confirmed |
| Session lifecycle is a lead | Repository lock: FastMCP 3.0.0, MCP SDK 1.24.0. Locally installed manager retains per-session transports; HTTP construction exposes no idle timeout | Inspect exact production packages and reproduce before claiming this causes the observed growth |
| Blocking upstream calls | `execute_operation` calls synchronous post/search code directly; async discovery, batch, and comment functions also perform synchronous network operations | A slow upstream can delay the event loop and health checks; independent of the memory-leak hypothesis |
| Client validation errors | 50 error-level app log lines: 42 tool-validation messages, 4 additional validation exception lines, 2 stream messages from one client disconnect, 1 resource error, 1 shutdown timeout | These are log-line counts, not 50 independent server outages |
| OAuth discovery fallback missing | Bare protected-resource metadata returns 404; advertised `/mcp`-suffixed route returns 200 | Add a compatibility route while preserving the existing metadata identity |

The coarse request metrics reported 9 502s, while complete request-log retrieval returned 118. Use request logs for this incident count; reconcile the aggregation discrepancy before publishing any percentage-based availability claim. Do not equate HTTP 200 with successful MCP operations: tool failures can be returned inside successful HTTP responses.

## Design choices

1. **Recommended: repair session cleanup while preserving stateful HTTP.** Prefer supported framework cleanup and idle expiry, with a targeted dependency update if necessary. This best preserves existing clients and progress reporting.
2. **Stateless HTTP is a fallback experiment.** Test only if stateful cleanup cannot be made reliable. It changes session and streaming behavior; a production switch requires presenting the compatibility results and revised design for approval.
3. **More RAM or periodic restarts are temporary mitigations.** Neither demonstrates that retained memory is bounded. The main plan keeps the current compute allocation and permits only the conditional preventive redeploy described above.

Current FastMCP documentation exposes `session_idle_timeout`, but the inspected installed version does not. Do not copy that option into production without identifying a compatible released version and verifying its behavior, including interaction with long-running requests. See [FastMCP HTTP API](https://gofastmcp.com/python-sdk/fastmcp-server-http).

## Task 1: Establish a reproducible baseline

**Files:** Create `scripts/soak_http.py`, `tests/test_http_lifecycle.py`, and a baseline report under `docs/operations/`. Read `src/http_server.py`, `src/server.py`, `pyproject.toml`, and `uv.lock`.

- [x] After approval, confirm the working tree is clean, create the named branch, and record the production deploy ID, commit, package versions, transport settings, instance start time, and memory limit. Read only the specific runtime settings needed; do not dump environment variables.
- [x] Preserve the known-good deploy reference: `dep-dadkbv3l550s73c4902g`, commit `3a4935aaed74df02ba23a917b8b3d2bd7030fea1`; refresh if production has changed.
- [x] Check whether the local HTTP server is already healthy. Start a separate background test server on an available localhost port if needed, using synthetic auth and stub upstreams. Never reuse live credentials for a stress test.
- [x] Install the locked environment and dev extras with `uv sync --frozen --extra dev`; run `uv run --frozen pytest -q`. Record pre-existing failures separately from regressions.
- [x] Exercise real HTTP transport: initialize, initialized notification, tools/list, tools/call, resource read, graceful DELETE, dropped connections without DELETE, cancelled POSTs, and idle or abandoned GET streams. Include valid and invalid session IDs and unsuccessful initialization.
- [x] Measure current RSS, Python allocations using tracemalloc in the isolated test process, task counts, retained sessions, open file descriptors, and thread counts after equal batches and a fixed idle period. Include an idle control with only `/health` traffic.
- [x] Run at least ten batches of 100 sessions with upstreams stubbed, then repeat representative operations with controlled upstream delays. Keep baseline and candidate workloads identical.
- [x] Produce a causal report: which workload retains objects, what owns them, which termination paths release them, and whether retained Python objects explain RSS. Investigate native allocations separately if RSS grows without corresponding Python growth.

**Deliverable:** A repeatable failure or an explicit evidence gap with a bounded diagnostic deployment proposal. If reproduction fails, continue investigation; do not label a speculative dependency change as the fix.

## Task 2: Add bounded runtime diagnostics and correct health semantics

**Files:** Create `src/observability.py` and `tests/test_observability.py`; modify `src/http_server.py`, the server lifespan wiring in `src/server.py`, and `tests/test_http_server.py`. Add a small runtime dependency for current RSS only if needed and lock it.

**Interface:** A lifespan-owned sampler emits `runtime_sample` structured logs once per minute with `uptime_seconds`, `rss_bytes`, `task_count`, `inflight_operations`, and `event_loop_lag_ms`. Add session counts only where the chosen SDK provides a stable mechanism; isolate any version-specific diagnostic adapter.

- [x] Test sampler startup, one sampler per process, stop/cancellation on shutdown, bounded storage, and omission of sensitive fields. Verification uses short real-clock sampling intervals and actual-entrypoint shutdown tests.
- [x] Emit operation completion records with operation name, elapsed milliseconds, and a bounded outcome category: success, invalid_input, upstream_timeout, upstream_rate_limit, cancelled, or internal_error. Include application-level `success: false` results.
- [x] Keep `/health` inexpensive and free of network calls. Return 503 when required local initialization is incomplete or the process is draining; return 200 when the process can serve requests.
- [x] Keep dependency probes out of Render's frequent restart decision. An upstream outage should generate a dependency alert rather than force healthy MCP processes into a restart loop.
- [x] Test that mock upstream outages do not make the local liveness probe block, and that local initialization failure cannot report healthy.

**Deliverable:** Production can reveal retained tasks and rising RSS without exposing a public diagnostic endpoint or adding another unbounded collection.

## Task 3: Repair the demonstrated session/resource leak

**Files:** Modify `src/http_server.py`, lifespan wiring in `src/server.py`, and, when justified, `pyproject.toml`/`uv.lock`. Extend `tests/test_http_lifecycle.py` and `scripts/soak_http.py`. Modify `src/chroma_client.py` or client ownership only if lifecycle evidence calls for it.

- [x] Trace the retention path from Task 1 and compare compatible FastMCP/MCP releases against the reproducer. Choose and record the smallest compatible released version pair that fixes the demonstrated problem; preserve `fastmcp <4` unless a revised design is approved.
- [x] Prefer supported stateful cleanup. Idle expiry: the supported MCP 1.30.0 default of 30 minutes. FastMCP 3.0 does not expose configuration, so this repair keeps the default without production monkeypatching. Test the framework's exact definition of inactivity and handling of open GET streams; do not assume an idle-timeout setting cleans up every abandoned connection.
- [x] Verify explicit DELETE, disconnect, cancellation, failed initialization, and idle expiry release both transports and associated tasks. If explicit termination still leaves retained entries, an idle timer alone does not satisfy this task.
- [x] Verify active calls are not terminated by idle cleanup and clients recover correctly from an expired session. Test at least Claude Code, the Dialog agent's MCP client, and a representative Cursor connection. Cursor coverage is transport-only because the installed old CLI ignores configured HTTP headers; independent signed-token HTTP tests cover authentication.
- [x] Pair client creation and teardown. Close the Chroma HTTP session before replacing its cached client; close owned Reddit/HTTP clients and the diagnostic sampler during lifespan shutdown. Preserve stdio ownership and avoid double initialization.
- [x] Exercise SIGTERM with both live GET streams and in-flight operations. Bound draining to the platform grace period, close idle streams, and account explicitly for any cancelled calls. Verify no leaked-task shutdown warning under the representative test.
- [x] Rerun the exact baseline harness against the candidate and capture before/after allocation ownership and resource counts.

**Deliverable:** A regression test fails on the baseline and passes on the chosen fix. Exact package changes and release evidence are included in the PR. Do not implement a custom session garbage collector by editing SDK private dictionaries.

## Task 4: Keep upstream calls off the event loop

**Files:** Create `src/blocking_io.py` and `tests/test_http_responsiveness.py`; modify the relevant boundaries in `src/server.py`, `src/config.py`, `src/chroma_client.py`, `src/tools/posts.py`, `src/tools/search.py`, `src/tools/comments.py`, `src/tools/discover.py`, and `src/resources.py`.

**Design:** Use a bounded, lifespan-owned worker for synchronous Reddit access and a separate bounded worker for Chroma access. Each upstream's synchronous client is owned by its worker; never use one requests/PRAW session concurrently across threads. Preserve progress notifications on the event loop. Fully materialize lazy upstream responses in the worker before returning plain data.

- [x] Write an HTTP test with an upstream stub that waits 10 seconds; concurrently issue 20 health requests. Demonstrate the baseline stall and require candidate health responses to finish within 1 second in the controlled local test.
- [x] Cover all five Reddit/vector operations, not just the synchronous dispatch branch. Keep async feed HTTP operations async and preserve their existing response contracts.
- [x] Start with one worker per upstream and at most 16 queued operations per worker. Reject excess work promptly with a structured retryable busy result; test no hidden executor queue grows past that bound.
- [x] Configure finite upstream request timeouts and bounded retries. Preserve Chroma's existing timeout bounds; explicitly test PRAW's rate-limit waiting behavior instead of allowing its current 300-second wait to monopolize the worker indefinitely.
- [x] Treat thread cancellation honestly: cancelling the awaiting coroutine does not kill a running network call. Keep its capacity occupied until the worker exits, discard late output, and rely on bounded upstream I/O. Verify shutdown behavior for that case.
- [x] Pass progress information back through bounded messages, invoke `ctx.report_progress` on the event loop, and test ordering, completion, cancellation, and error propagation.
- [x] Confirm response schemas and result limits are unchanged. This task does not include a general AsyncPRAW migration or a rewrite of feed persistence.

**Deliverable:** Slow or rate-limited upstreams produce bounded failures while `/health`, authentication, and unrelated MCP operations remain responsive.

## Task 5: Restore the OAuth discovery fallback

**Files:** Modify `src/server.py` and `tests/test_http_server.py`.

- [x] Add a failing parameterized test for both public metadata paths returning 200 and the same JSON document. Test localhost and configured hosted `SERVER_URL` values, including trailing slashes.
- [x] Register `/.well-known/oauth-protected-resource` alongside `/.well-known/oauth-protected-resource/mcp`, sharing the existing response implementation.
- [x] Preserve the `/mcp` resource identity, Descope authorization-server URL, and bearer challenge. Check framework/custom route precedence so neither path shadows the wrong response.
- [x] Test unauthenticated MCP access remains 401; both supported issuer formats still authenticate; invalid, expired, and incorrectly signed tokens remain rejected. Use synthetic signing keys and local JWKS fixtures.
- [ ] Verify the canonical and legacy hosts advertise their own configured resource identities after deployment.

**Deliverable:** Compatible public discovery at both paths with authentication behavior preserved.

## Task 6: Add monitoring with a tested notification path

**Files:** Create `scripts/check_production.py`, `tests/test_production_monitor.py`, `.github/workflows/production-uptime.yml`, and `docs/operations/production-reliability.md`; update `render.yaml` with one separate monitoring cron service.

**Primary monitor:** A Render cron job every five minutes checks the canonical health URL, both OAuth metadata routes, and fresh Render memory/request metrics for the MCP service. Use short network timeouts, a 90-second whole-run limit, and a minimal dependency environment. A monitoring API failure or stale/missing telemetry is an explicit monitoring failure, never a healthy result.

| Signal | Proposed threshold / response |
| --- | --- |
| Public health or metadata failure | Retry twice within the run; alert if still failing |
| Memory warning | At least 75% for 10 minutes |
| Memory critical | At least 85% for 10 minutes |
| Process restart | Alert on an unexpected runtime boot record; annotate planned deployments |
| HTTP 5xx | Alert on at least 5 in 5 minutes, or over 1% with at least 100 requests |
| Tool failures inside HTTP 200 | Alert on at least 5 internal/upstream-timeout outcomes in 5 minutes; exclude invalid input and expected auth challenges |
| Missing telemetry | No fresh metric samples within 15 minutes, missing expected runtime samples, or checker/API failure |

- [x] Parse actual Render API responses into pure threshold-evaluation functions; test exact boundary values, multiple instances during deployment, stale data, absent series, and a valid zero-error interval. Pin resource/workspace IDs in configuration.
- [x] Use current usage divided by current limit per instance; never add both deployment instances' memory and compare against one instance's limit. Use request logs where the coarse metric discrepancy would affect an alert.
- [x] Read bounded log windows for boot records, application outcomes, and missing runtime samples. Apply timeouts and pagination limits; incomplete data marks monitoring incomplete.
- [x] Store the monitor's Render credential only as a service secret. Use read-only/scoped credentials where supported; if Render offers only a broader API key, disclose the effective scope before provisioning it and give the checker code no mutation path.
- [ ] Configure service-level failure notifications to Chris's existing Render email destination. Threshold breaches cause the cron job to fail with a concise diagnostic summary, invoking Render's failure notification path. Initially allow repeated alerts while a condition persists; document observed delivery and repeat behavior instead of assuming deduplication.
- [ ] Add a credential-free GitHub Actions check of public health and metadata every five minutes, offset from the hour, as an independent platform-outage signal. Configure failure notifications for Chris and verify delivery. This is supplementary: GitHub scheduling can be delayed/dropped and public-repo schedules can disable after 60 days of inactivity.
- [ ] Use the authenticated connector for read-only post-deploy and daily soak smoke checks: discovery, one fetched post, resource read, and a feed-list read where available. Do not store a personal connector token in a public-repo scheduled workflow. Durable unattended authenticated synthetic testing needs a dedicated renewable monitor identity and is a separate follow-up if no suitable identity exists.
- [ ] Send a labeled test failure through the real alert path, verify receipt, then restore passing checks. Simulate warning, critical, stale metrics, and upstream failures using fixtures; never exhaust production memory to test alerts.
- [ ] Verify actual cron compute cost stays within the approved $5/month allowance. Smallest-plan cron compute is listed at $0.00016/minute with a $1/month minimum; 90 seconds per five-minute run is about $2.15 for a 31-day month, excluding ancillary charges. Recheck current rates and actual usage after provisioning.

**Deliverable:** Warning and critical conditions generate a received notification. A dashboard chart or a warning log alone does not satisfy alert delivery. Render-hosted monitoring has a shared-platform failure risk; the external check reduces that risk without claiming guaranteed detection latency.

Sources: [Render notifications](https://render.com/docs/notifications), [cron jobs and minimum charge](https://render.com/docs/cronjobs), [compute pricing](https://render.com/pricing), [GitHub scheduled-workflow limitations](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule).

## Task 7: Add a release gate and assemble the PR

**Files:** Create `.github/workflows/test.yml`; update the operational runbook and baseline/candidate reports.

- [x] Run PR tests on Python 3.11 and 3.12 using locked dev dependencies and synthetic auth/upstreams. Include HTTP lifecycle, responsiveness, OAuth, monitoring, and existing operation tests. No production secrets in PR jobs.
- [x] Run `uv run --frozen pytest -q` and `uv build`; verify both console entrypoints from the resulting package.
- [x] Run a two-hour, 512 MiB-limited candidate soak with steady work and repeated session churn. Use short test-only expiry intervals for deterministic cleanup checks, and separately verify the production idle timeout configuration.
- [x] Require no monotonic growth in retained sessions/tasks/file descriptors after cleanup, no OOM, and post-warmup RSS growth below 10 MiB/hour. Compare allocation snapshots and equal-work batches; this short soak is only a predeployment gate, not final proof.
- [x] Confirm p95 health latency below 1 second under simulated slow upstream calls and no material regression in representative operation latency or throughput against the same baseline workload. Candidate health p95: 16.4 ms; baseline concurrent health duration: 9.93 seconds. Equal-work session harness elapsed changed by approximately 3.6%.
- [x] Review the final diff for auth compatibility, cancellation semantics, queue bounds, package changes, and rollbackability. Present test results in the PR. If any baseline failure remains, resolve it or explicitly revise the gate before merging.

**Deliverable:** One focused PR containing independently reviewable commits for diagnostics/cleanup, responsiveness, OAuth, and monitoring. Preserve the unrelated package-publishing workflow.

## Task 8: Controlled rollout and rollback

- [ ] Refresh production health/memory and record the previous deploy and configuration. If the conditional 85% mitigation threshold is reached before the fix is ready, capture diagnostics and perform the authorized known-good redeploy; record it separately from fix validation.
- [ ] Merge only after the automated and manual gates pass. `main` auto-deploys on Render and also affects the legacy deployment; watch both. Do not trigger a duplicate deploy after the auto-deploy begins.
- [ ] Confirm new-instance health before traffic is routed; verify runtime versions, configuration, metadata, auth, small discovery/post/comment operations, progress delivery, resource read, and feed-list behavior. Observe reconnect behavior for a pre-existing session.
- [ ] Observe the first 30 minutes: no sustained health failures, no memory surge, no broad auth failures, no persistent tool-error increase, and expected completion/cancellation of old-instance work. Bring the monitoring cron live and test its alert path.
- [ ] Roll back immediately for failed authentication/client compatibility, sustained health failures over 60 seconds, any OOM, or 5xx/internal-error rates meeting the monitoring incident threshold in two consecutive five-minute windows attributable to the release. Also roll back a material latency regression reproduced against the same workload.
- [ ] Restore the last known-good service deploy and changed runtime settings, then revert the responsible main-branch change so auto-deploy cannot reintroduce it. Verify the legacy deployment separately; its deploy controls differ from Render. Preserve incident evidence.
- [ ] Repeat the same read-only smoke checks after rollback. Document that rollback can restore the old memory leak; keep the temporary mitigation rule and alerts active until a corrected release is ready.

Render starts routing to a new instance only after successful health checks; existing long-lived MCP sessions can still need to reconnect. This plan improves reliability on one instance and does not promise high availability during every deployment or platform failure. See [Render health checks](https://render.com/docs/health-checks).

## Task 9: Prove stability over seven days

- [ ] Capture comparable observations at 1 hour, 24 hours, 72 hours, and 7 days. Scheduled monitors continue independently; the executing agent must not claim it will remain active after its session ends. Name the operational owner in the runbook (Chris receives alerts).
- [ ] Require seven continuous days with no OOM or unexplained restart, zero recurrence of the retained-session defect, successful daily authenticated smoke checks, and no sustained server-error incidents.
- [ ] Require memory below 75% of the cap and a post-warmup seven-day trend no greater than 5 MiB/day under comparable traffic, with equal-work/idle snapshots showing bounded retained objects. This is an operational acceptance threshold, not mathematical proof of zero leakage.
- [ ] Exclude the first six hours of warmup from the production slope; correlate request volume, active sessions, and deployments. Do not declare success simply because a restarted process has low RSS or traffic disappeared.
- [ ] Verify warning/critical notification delivery and checker continuity. Record any GitHub schedule interruption and confirm the primary cron continued.
- [ ] Mark status as “deployed; stability verification pending” until the seven-day window passes. If criteria fail, keep the issue open, retain evidence, and resume investigation.

**Final deliverables:** Merged remediation PR, locked dependency changes with evidence, HTTP/lifecycle/soak tests, received alert test, deployment/rollback record, operator runbook, and seven-day stability report.

## Execution order and timing

1. After approval: branch, fresh production baseline, failure notifications, and the local reproducer. Surface rising memory immediately.
2. Implement and test diagnostics plus the evidenced session fix; separately address blocking I/O and OAuth fallback. Prepare monitoring alongside these changes.
3. Complete the two-hour soak and PR gates, then deploy and observe the first 30 minutes.
4. Continue automated checks and the seven-day acceptance window.

Working estimate: 1–3 engineering days if a compatible framework cleanup fix resolves the reproducer, followed by seven days of observation. If the leak is elsewhere or cleanup changes break existing clients, report that evidence and revise the implementation estimate before broadening the design. The September 11 projection is a reason to install alerts and preserve headroom, not a reason to bypass validation.
