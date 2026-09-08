# Production MCP rollout — September 8, 2026

Status: **deployed; stability verification pending**. The first 30-minute
observation window passed. Email receipt is not yet confirmed.

## Release references

- Repair PR: https://github.com/dialog-tools/reddit-research-mcp/pull/27
- Tested PR head: `89d44b90c5776a7ae776a058ca4596eafea5f89b`.
- Production commit: `57ea82ed8f4cd7eaf0c3e341d60e03a0e4b21bd1`.
- Render deploy: `dep-daft2umq1p3s73ebfa50`, live at
  **2026-09-08 09:13:26 UTC / 02:13:26 Pacific**.
- New instance: `srv-d9vekctg1s2s73fbr4l0-wtc8w`.
- Previous deploy: `dep-dadkbv3l550s73c4902g`; previous commit:
  `3a4935aaed74df02ba23a917b8b3d2bd7030fea1`.
- Applied platform shutdown allowance: 60 seconds, previously default 30.
  The service remains one starter instance with a 512 MiB limit.

Main auto-deployed once on Render. No duplicate application deploy was triggered.
The legacy host also began serving the added metadata fallback. Its dashboard
and actual runtime package versions remain unverified because administrative
access was unavailable.

## Validation

- Python 3.11/3.12: all 119 tests and package builds passed on the final PR head.
  [Final CI run](https://github.com/dialog-tools/reddit-research-mcp/actions/runs/34208531938).
- The 512 MiB, no-extra-swap container passed 7,201.57 seconds and 320 batches:
  no OOM, exit zero, zero retained sessions, seven tasks, five threads, ten open
  file descriptors, and post-warmup RSS fixed at 122.44 MiB (0 MiB/hour slope).
- The separate unmodified 30-minute SDK expiry test passed: abandoned session
  released, expired session returned 404, and a fresh session worked.
- Production runtime verified through the service's environment: Python 3.12.7,
  FastMCP 3.0.0, MCP 1.30.0, SSE Starlette 3.4.11, Starlette 0.49.3, psutil 7.2.2.
- The existing authenticated connector continued working across deployment.
  Operation discovery, a small vector search, one Reddit post, one comment,
  the server-info resource, and feed listing all succeeded. No production
  writes were performed by the smoke checks.
- Both metadata routes return matching, host-specific resource identities on
  both hosts. Unauthenticated initialization returns 401 on both. The legacy
  platform disallows GET `/mcp` with 405; its POST authentication was checked.
- Actual HTTP progress delivery was verified in the isolated release tests.
  Production async operations succeeded, but the connector interface does not
  expose individual progress notifications for independent delivery inspection.

The retiring old instance `...-k8qc4` hit its existing graceful-shutdown timeout
and cancelled 46 tasks. All 47 timeout-related log lines were attributed to that
old instance. It was deactivated; the new instance emitted one boot record and
fresh runtime samples. This does not establish production shutdown behavior for
the new version; its real SIGTERM tests cover that behavior locally.

## First 30-minute result

From 09:13:27 through 09:43:27 UTC, all 232 sampled public health checks passed
(116 per host). Canonical health p95 was 276 ms; legacy p95 was 476 ms. Complete
request-log retrieval in six five-minute windows returned 782 unique requests
and zero HTTP 5xx responses. There were no native platform failures or additional
runtime boots. The new instance was running and ready at the end of the window.

Process RSS ranged from 98.01 to 104.56 MiB during startup and warmup; final
Render memory usage was 117.56 MiB of 512 MiB. The final event-loop lag sample
was 0.6 ms. Four recorded operation completions were successful. No rollback
threshold was met. These observations do not replace the seven-day acceptance
window or prove a long-term production memory slope.

Evidence: `production-rollout-30-minute-result.json`,
`production-rollout-health.jsonl`, `production-rollout-runtime.json`, and
`postdeploy-public-identity.json`.

## Monitoring and delivery

The Render monitor `crn-dafrbr8n74is73baeqq0` follows main, runs every five
minutes, and uses the smallest `0.5c-512mb` plan. Its initial code was deployed as
`dep-daft4vtg1s2s7383837g`. The normal manual run finished successfully at
09:17:51 UTC; the first scheduled run finished successfully at 09:20:28 UTC.

The 09:25 run exposed a false telemetry alert: Render still returned the retired
instance's memory series, whose shrinking historical window was treated as
incomplete current data. The correction selects Render's current-instance
inventory and requires fresh telemetry for every listed instance. Four new
regression tests cover this case and missing/stale current telemetry; all 123
tests passed on Python 3.11 and 3.12. The corrected cron deploy
`dep-daftb7ad0e5s73duletg` passed a manual run at 09:31:52 and a scheduled run at
09:35:24 UTC. The application runtime is unchanged by this monitor-only fix.

Its labeled failure test ran at 07:16 UTC. The independent GitHub labeled test
[failed intentionally](https://github.com/dialog-tools/reddit-research-mcp/actions/runs/34209090034)
at 09:16 UTC, and the subsequent
[normal public check passed](https://github.com/dialog-tools/reddit-research-mcp/actions/runs/34209158121).
These prove the checks reach their failure/success states. **Email receipt for
both channels remains unconfirmed.** Chris's existing Render email settings are
enabled; GitHub email preferences could not be verified with the available scope.
The GitHub workflow is active and its manual check passed; its first scheduled
run had not appeared by the end of this observation window. Schedule execution
remains an explicit follow-up; the primary Render cron is running successfully.

The first normal Render run took approximately 20 seconds including startup;
the checker itself took approximately 2.5 seconds. Observed runtime is consistent
with the $1/month minimum at current pricing; the configured checker-runtime
estimate is approximately $2.15/month at its maximum duration, plus platform
startup/teardown and any ancillary charges. Observed total run times are
consistent with the authorized $5 allowance.
This is a runtime-based cost estimate, not a finalized monthly invoice.

## Acceptance checkpoints and owner

Chris owns alert response and daily small authenticated read-only checks.
Automated monitors continue after this agent session ends. A renewable unattended
authenticated monitor identity has not been provisioned.

| Checkpoint | Due (UTC) | Status |
| --- | --- | --- |
| First 30 minutes | September 8, 09:43:26 | Passed |
| 1 hour | September 8, 10:13:26 | Pending |
| 24 hours | September 9, 09:13:26 | Pending |
| 72 hours | September 11, 09:13:26 | Pending |
| Seven days | September 15, 09:13:26 | Pending |

Exclude the first six hours from the production RSS trend. Require no OOM or
unexplained restart, no sustained server-error incident, daily authenticated
checks, memory below 75%, and growth no greater than 5 MiB/day under comparable
traffic. Follow the rollback thresholds in `production-reliability.md` if these
criteria fail. A short soak and low memory immediately after a deployment do not
establish seven-day reliability.
