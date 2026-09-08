"""Read-only production checks. Stdlib only; nonzero exit triggers cron alerts."""
import argparse
from datetime import datetime, timedelta, timezone
import json
import math
import os
import signal
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

SERVICE = "srv-d9vekctg1s2s73fbr4l0"
WORKSPACE = "tea-d1rmi0p5pdvs73ea4dvg"
ORIGIN = "https://mcp.dialog.tools"
API = "https://api.render.com/v1"


class MonitoringError(RuntimeError):
    pass


def timestamp(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def finding(signal_name, detail, severity="critical"):
    return {"signal": signal_name, "severity": severity, "detail": detail}


def instance(series):
    return next((l["value"] for l in series["labels"] if l["field"] == "instance"), None)


def evaluate_memory(usage, limits, now, warming_instances=()):
    findings = []
    fresh = [s for s in usage if s.get("values") and
             0 <= (now-timestamp(s["values"][-1]["timestamp"])).total_seconds() <= 900]
    if not fresh:
        return [finding("telemetry", "Memory samples missing or stale")]
    limit_by_instance = {instance(s): s for s in limits}
    for s in fresh:
        limit = limit_by_instance.get(instance(s))
        if not limit or not limit.get("values") or (now-timestamp(limit["values"][-1]["timestamp"])).total_seconds() > 900:
            findings.append(finding("telemetry", "Memory limit missing or stale"))
            continue
        cap = limit["values"][-1]["value"]
        if not isinstance(cap, (int, float)) or not math.isfinite(cap) or cap <= 0:
            findings.append(finding("telemetry", "Invalid memory limit"))
            continue
        values = s["values"]
        latest = timestamp(values[-1]["timestamp"])
        window = [v for v in values if (latest-timestamp(v["timestamp"])).total_seconds() <= 600]
        times = [timestamp(v["timestamp"]) for v in window]
        if len(times) < 2 or (times[-1]-times[0]).total_seconds() < 600 or any(
                not 0 < (b-a).total_seconds() <= 90 for a,b in zip(times,times[1:])):
            if instance(s) in warming_instances and times and all(
                    0 < (b-a).total_seconds() <= 90 for a,b in zip(times,times[1:])):
                # A confirmed deployment may not yet have ten minutes of data.
                # Missing or stale data still fails above; never infer stability.
                continue
            findings.append(finding("telemetry", "Insufficient continuous memory history"))
            continue
        ratios = [v["value"]/cap for v in window]
        if any(not math.isfinite(r) or r < 0 for r in ratios):
            findings.append(finding("telemetry", "Invalid memory usage"))
        elif min(ratios) >= .75:
            findings.append(finding("memory", f"{instance(s)}: {ratios[-1]:.0%} memory for 10 minutes",
                                    "critical" if min(ratios) >= .85 else "warning"))
    return findings


def evaluate_http(errors, total):
    if errors >= 5 or (total >= 100 and errors/total > .01):
        return [finding("http", f"{errors} server errors in {total} requests over five minutes")]
    return []


def evaluate_operations(records):
    errors = sum(r.get("outcome") in {"internal_error", "upstream_timeout"} for r in records)
    return [finding("operations", f"{errors} operation failures in five minutes")] if errors >= 5 else []


def classify_boots(boots, deploys, now):
    """Allow one boot inside each deployment's actual build/start interval."""
    findings, warming, used_deploys = [], set(), set()
    for boot in sorted(boots, key=lambda b: b["timestamp"]):
        boot_time = timestamp(boot["timestamp"])
        planned = None
        for entry in deploys:
            deploy = entry.get("deploy", entry)
            if deploy.get("status") not in {"live", "update_in_progress"}:
                continue
            end = timestamp(deploy["finishedAt"]) if deploy.get("finishedAt") else now
            if timestamp(deploy["createdAt"]) <= boot_time <= end+timedelta(seconds=60):
                planned = deploy["id"]
                break
        if planned and planned not in used_deploys:
            used_deploys.add(planned)
            if boot.get("instance") and (now-boot_time).total_seconds() < 600:
                warming.add(boot["instance"])
        elif (now-boot_time).total_seconds() <= 300:
            findings.append(finding("restart", "Unexpected runtime boot in last five minutes"))
    return findings, warming


def require_complete_logs(data):
    if data.get("hasMore") is not False or not isinstance(data.get("logs"), list):
        raise MonitoringError("Incomplete log query")
    return data["logs"]


def get_json(url, token=None):
    headers = {"User-Agent": "Dialog-MCP-Reliability/1", "Accept": "application/json"}
    if token:
        # A Render credential is never sent to a monitored service or a redirect.
        if not url.startswith(API+"/"):
            raise MonitoringError("Credential destination rejected")
        headers["Authorization"] = "Bearer " + token
    from urllib.request import HTTPRedirectHandler, build_opener
    class NoRedirect(HTTPRedirectHandler):
        def redirect_request(self, *args, **kwargs):
            return None
    with build_opener(NoRedirect).open(Request(url, headers=headers), timeout=10) as response:
        body = response.read(4*1024*1024+1)
        if len(body) > 4*1024*1024:
            raise MonitoringError("Response exceeded monitoring size limit")
        return json.loads(body)


def api_get(path, token, **params):
    return get_json(API+path+("?"+urlencode(params, doseq=True) if params else ""), token)


def iso(value):
    return value.strftime("%Y-%m-%dT%H:%M:%SZ")


def read_logs(token, now, minutes, **filters):
    params = {"ownerId": WORKSPACE, "resource": SERVICE, "startTime": iso(now-timedelta(minutes=minutes)),
              "endTime": iso(now), "direction": "backward", "limit": 1000, **filters}
    entries = {}
    for _ in range(3):
        data = api_get("/logs", token, **params)
        for log in data.get("logs", []):
            entries[log["id"]] = log
        if data.get("hasMore") is False:
            require_complete_logs(data)
            return list(entries.values())
        next_end = data.get("nextEndTime")
        if not next_end or next_end == params["endTime"]:
            break
        params["endTime"] = next_end
    raise MonitoringError("Log pagination exceeded bounded query; result incomplete")


def structured_logs(logs):
    parsed = []
    for log in logs:
        message = log.get("message", "")
        start = message.find("{")
        if start < 0:
            continue
        try:
            record = json.loads(message[start:])
        except json.JSONDecodeError:
            continue
        if isinstance(record, dict):
            label = next((v["value"] for v in log.get("labels", []) if v["name"] == "instance"), None)
            parsed.append({**record, "timestamp": log["timestamp"], "instance": label})
    return parsed


def check_public():
    findings = []
    for path in ["/health", "/.well-known/oauth-protected-resource", "/.well-known/oauth-protected-resource/mcp"]:
        for attempt in range(3):
            try:
                body = get_json(ORIGIN+path)
                if path == "/health":
                    valid = body.get("status") == "ok"
                else:
                    valid = body.get("resource") == ORIGIN+"/mcp" and bool(body.get("authorization_servers"))
                if not valid:
                    raise MonitoringError("Unexpected response body")
                break
            except (HTTPError, URLError, TimeoutError, ValueError, MonitoringError):
                if attempt == 2:
                    findings.append(finding("public", f"{path} failed three checks"))
                else:
                    time.sleep(1)
    return findings


def check_private(token, now):
    service = api_get("/services/"+SERVICE, token)
    if service.get("ownerId") != WORKSPACE:
        raise MonitoringError("Service workspace mismatch")
    params = {"resource": SERVICE, "startTime": iso(now-timedelta(minutes=20)),
              "endTime": iso(now), "resolutionSeconds": 60}
    usage = api_get("/metrics/memory", token, **params)
    limits = api_get("/metrics/memory-limit", token, **params)
    runtime = structured_logs(read_logs(token, now, 15, type="app", text="runtime_"))
    boots = [r for r in runtime if r.get("event") == "runtime_boot"]
    deploys = api_get("/services/"+SERVICE+"/deploys", token, limit=5) if boots else []
    findings, warming = classify_boots(boots, deploys, now)
    findings.extend(evaluate_memory(usage, limits, now, warming))
    requests = read_logs(token, now, 5, type="request")
    errors = sum(any(l["name"] == "statusCode" and l["value"].startswith("5") for l in r["labels"]) for r in requests)
    findings.extend(evaluate_http(errors, len(requests)))
    operations = structured_logs(read_logs(token, now, 5, type="app", text="operation_complete"))
    findings.extend(evaluate_operations(operations))
    if not any(r.get("event") == "runtime_sample" for r in runtime):
        findings.append(finding("telemetry", "No runtime sample in 15 minutes"))
    return findings


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--public-only", action="store_true")
    parser.add_argument("--test-alert", action="store_true")
    args = parser.parse_args(argv)
    if args.test_alert:
        print(json.dumps({"status":"test_alert", "detail":"Approved Dialog MCP notification delivery test"}), flush=True)
        return 1
    if hasattr(signal, "SIGALRM"):
        def deadline(*_):
            print(json.dumps({"status":"monitor_failure", "detail":"85-second checker deadline exceeded"}), flush=True)
            os._exit(2)
        signal.signal(signal.SIGALRM, deadline)
        signal.alarm(85)
    try:
        findings = check_public()
        if not args.public_only:
            token = os.environ.get("RENDER_API_KEY")
            if not token:
                raise MonitoringError("Render monitoring credential missing")
            findings.extend(check_private(token, datetime.now(timezone.utc)))
        print(json.dumps({"status":"alert" if findings else "healthy", "findings":findings}), flush=True)
        return 1 if findings else 0
    except Exception as exc:
        # Never print arbitrary upstream bodies, URLs, or exception text.
        print(json.dumps({"status":"monitor_failure", "error_type":type(exc).__name__}), flush=True)
        return 2
    finally:
        if hasattr(signal,"SIGALRM"):
            signal.alarm(0)


if __name__ == "__main__":
    sys.exit(main())
