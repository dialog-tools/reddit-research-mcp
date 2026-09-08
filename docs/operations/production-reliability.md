# Production reliability runbook

Status: implementation and release validation in progress. Production rollout,
alert delivery verification, and the seven-day stability window remain pending.
Chris is the operational owner and receives alerts through his existing Render
account email destination.

## Service and release references

| Component | Reference |
| --- | --- |
| Canonical HTTP endpoint | https://mcp.dialog.tools/mcp |
| Liveness/readiness | https://mcp.dialog.tools/health |
| Render workspace | `tea-d1rmi0p5pdvs73ea4dvg` |
| Render MCP service | `srv-d9vekctg1s2s73fbr4l0`, 512 MiB starter, one instance |
| Vector dependency | `srv-d2jce1re5dus738ueaug` |
| Previous known-good deploy | `dep-dadkbv3l550s73c4902g` |
| Previous commit | `3a4935aaed74df02ba23a917b8b3d2bd7030fea1` |
| Legacy host | https://reddit-research-mcp.fastmcp.app/mcp |
| Monitor | `reddit-mcp-reliability-monitor` (provisioning pending) |

Both hosted deployments follow `main`. A merge may deploy both. Avoid manually
triggering a second Render deploy after auto-deploy starts. This remains a
single-instance service; long-lived client sessions can need reinitialization
during a deployment.

## What the repair changes

- FastMCP stays at **3.0.0**. MCP SDK moves from **1.24.0 to 1.30.0**.
  The SDK now discards terminated/failed sessions and expires abandoned sessions
  after its supported **30-minute default**. Active POSTs and open GET streams
  pause expiry. FastMCP 3.0 does not expose a configurable SDK idle timeout; this
  repair uses the SDK default without modifying production SDK internals.
- SSE Starlette moves from **3.0.2 to 3.4.11**, with Starlette **0.49.3** locked.
  The old SSE shutdown watcher did not close established streams on SIGTERM.
  The new watcher is bounded to one per event loop. HTTP draining allows 25
  seconds, followed by concurrent worker draining for up to 26 seconds.
  The Render entrypoint serves `mcp.http_app()` directly through Uvicorn so its
  lifespan exits before Uvicorn re-raises SIGTERM; FastMCP 3.0's extra outer
  lifespan otherwise skips application cleanup on this path.
- Reddit and Chroma each have one owning worker thread and at most 16 queued
  operations. Cancelling a caller keeps running work's capacity occupied until
  it returns. Full queues return a retryable busy result. Progress notifications
  return to the original event loop with the originating request context intact.
- Reddit connect/read waits are capped at 10 seconds each. Its normal finite
  retry strategy remains in place. API rate-limit sleeps are disabled, and
  cached exhausted quotas are rejected before operations and individual PRAW
  requests (including pagination). PRAW may still pace requests or perform
  internal retries; these socket limits are not a whole-operation deadline.
  Python cannot kill an active worker thread. Daemon workers bound process exit
  even if an upstream stalls beyond the drain window; such calls can be cancelled.
- Owned HTTP sessions and the sampler close during lifespan shutdown. `/health`
  makes no external calls and returns 503 before local initialization or while
  the lifespan is draining. Dependency outages do not make this probe perform
  network calls or force a restart loop.
- Both public OAuth resource metadata paths serve the configured host's identity.
  Both Descope issuer formats remain accepted. `reddit://server-info` now returns
  JSON text, fixing its pre-existing FastMCP 3 resource-serialization error.

Sources: [MCP SDK 1.30.0 release](https://github.com/modelcontextprotocol/python-sdk/releases/tag/v1.30.0),
[SSE shutdown report](https://github.com/sysid/sse-starlette/issues/149),
[bounded watcher fix](https://github.com/sysid/sse-starlette/pull/153),
[SSE 3.4.11 release](https://github.com/sysid/sse-starlette/releases/tag/v3.4.11).

## Signals and alerts

The primary Render cron runs every five minutes using Python's standard library.
It checks public health and both metadata paths, memory and limit metrics per
instance, complete bounded request-log windows, structured operation outcomes,
and fresh runtime samples. It retries failed public checks twice, limits each
network request to ten seconds, and exits by 85 seconds.

| Signal | Alert condition |
| --- | --- |
| Public endpoints | Still failing after three attempts |
| Memory warning | At least 75% for ten continuous minutes |
| Memory critical | At least 85% for ten continuous minutes |
| HTTP failures | At least five 5xx in five minutes, or over 1% with at least 100 requests |
| Tool failures inside HTTP 200 | At least five internal-error/upstream-timeout outcomes in five minutes |
| Restarts | Unexpected runtime boot; one boot inside a deployment interval is planned |
| Missing telemetry | No fresh metrics/runtime samples within 15 minutes, missing limits, gaps, incomplete logs, or API/checker failure |

Do not add overlapping deployment instances' memory and compare their sum with
one instance's limit. A confirmed new deployment gets up to ten minutes to
accumulate continuous memory history; absent/stale data still fails. Restart
correlation uses a bounded 15-minute log window and the platform's deployment
timestamps; it is an operational heuristic, not a definitive OOM classifier.

Monitor exit codes are 0 (healthy), 1 (threshold/test alert), and 2 (checker or
telemetry query failure). Any nonzero result fails the cron and uses Render's
service failure notification path. Repeated alerts are permitted while a
condition persists; actual delivery and repeat behavior must be recorded after
the alert test, not inferred from a failed job alone.

The Render API key has account-level permissions broader than the checker
needs. It is supplied only as a service secret and only to the Render API.
The checker contains no mutation path, rejects redirects, bounds response sizes,
and omits arbitrary upstream errors/bodies from logs. Rotate the service secret
if that key is rotated; never put it into git or a public workflow.

The credential-free GitHub `Production public checks` workflow runs at minutes
2, 7, 12, and so on. It checks public endpoints from a separate platform. Chris's
GitHub Actions email preferences control its delivery. Scheduled jobs may be
delayed/dropped; public-repository schedules can disable after 60 days of
inactivity. This is a supplementary check, not a guaranteed five-minute SLO.

Run manual checks with:

```sh
python scripts/check_production.py --public-only
# With RENDER_API_KEY already provided through the environment:
python scripts/check_production.py
# Intentional labeled alert; only run when testing notification delivery:
python scripts/check_production.py --test-alert
```

Never store a personal MCP connector token in a scheduled workflow. Daily
authenticated checks need Chris/an active operator or a dedicated renewable
monitor identity. That identity is not provisioned by this repair.

Monitoring budget: at most $5/month incremental. Smallest cron compute is
$0.00016/minute with a $1/month minimum; the 90-second maximum every five minutes
would be about $2.15 of compute over 31 days. Check actual usage after provisioning.
Sources: [Render cron jobs](https://render.com/docs/cronjobs),
[Render pricing](https://render.com/pricing),
[Render notifications](https://render.com/docs/notifications),
[GitHub scheduling limitations](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule).

## Diagnostics without request contents

`reddit_mcp.runtime` emits JSON boot/shutdown records, one runtime sample per
minute, and operation completion records. Samples contain current RSS, uptime,
task count, in-flight operation count, and event-loop lag. Operation records
contain only the normalized operation name, duration, and outcome. No token,
request body, feed content, user ID, or unbounded history is collected.

Use raw request logs for incident counts. The August 31 audit found 118 actual
502 request logs where coarse metrics reported nine; percentage availability
must not use inconsistent numerators and denominators. Invalid input and
expected 401 challenges are not server outages. Partial operation responses
retain their existing contracts; the completion classifier is not a count of
every item-level failure embedded in a batch.

## Release and rollback gates

Before merge: Python 3.11/3.12 tests, package/entrypoint checks, real HTTP auth,
session lifecycle, progress, slow-upstream responsiveness, and a two-hour soak
under a 512 MiB memory limit. The soak uses synthetic auth and upstream stubs;
production credentials are never passed into its container. Require zero
retained sessions after expiry, bounded tasks/threads/file descriptors, no OOM,
and post-warmup RSS growth below 10 MiB/hour. Inspect the final diff before merge.

For a rollout, preserve the prior deploy/configuration and observe both hosts.
Check unauthenticated 401, both metadata documents, authenticated discovery,
one post/comment read, progress, server-info resource, and feed-list read.
Confirm reconnect behavior and runtime package versions, then observe 30 minutes.

Roll back for broken auth/client compatibility, health failure lasting over
60 seconds, any OOM, two consecutive five-minute incident windows attributable
to this release, or a reproduced material latency regression. Restore the
known-good Render deploy and changed settings, revert the responsible `main`
change to prevent redeployment, and verify the legacy host separately. Repeat
small authenticated read-only smoke checks. Preserve logs and metrics.

Rollback restores the old leak. If memory remains at least 85% for ten minutes
before a tested fix is available, the approved temporary mitigation is one
operator-run redeploy of the known-good code after capturing evidence. Verify
reconnection afterward. Do not schedule recurring restarts or increase compute
without a revised proposal.

## Seven-day acceptance record

Status remains **deployed; stability verification pending** after a successful
rollout until this window passes. Collect observations at 1 hour, 24 hours,
72 hours, and seven days, with daily authenticated read-only smoke checks.
Exclude the first six hours from the production RSS slope and compare traffic.
Require no OOM/unexplained restart, no sustained server-error incident, memory
below 75% of capacity, and growth no greater than 5 MiB/day under comparable work.
The short synthetic soak is a release gate, not proof of seven-day stability.

Scheduled monitors continue independently. An executing coding-agent session
does not remain active after it ends. Chris owns alert response and daily
authenticated checks until a renewable monitoring identity exists.

| Checkpoint | Evidence/status |
| --- | --- |
| Deployment and first 30 minutes | Pending |
| Render labeled alert receipt | Pending |
| GitHub labeled alert receipt | Pending |
| 1 hour | Pending |
| 24 hours | Pending |
| 72 hours | Pending |
| Seven days | Pending |
