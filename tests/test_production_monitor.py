from datetime import datetime, timezone, timedelta
import pytest

NOW = datetime(2026, 9, 8, 7, tzinfo=timezone.utc)


def series(value, instance="one", age=0):
    return {"labels": [{"field": "instance", "value": instance}], "unit": "bytes",
            "values": [{"timestamp": (NOW-timedelta(seconds=age+600-i*60)).isoformat(),
                        "value": value} for i in range(11)]}


@pytest.mark.parametrize("usage,severity", [(74, None), (75, "warning"), (85, "critical")])
def test_memory_sustained_boundaries(usage, severity):
    from scripts.check_production import evaluate_memory
    findings = evaluate_memory([series(usage)], [series(100)], NOW)
    assert [f["severity"] for f in findings] == ([] if severity is None else [severity])


def test_memory_is_per_instance_and_short_spike_does_not_alert():
    from scripts.check_production import evaluate_memory
    one, two = series(60), series(60, "two")
    two["values"][-1]["value"] = 95
    assert evaluate_memory([one, two], [series(100), series(100, "two")], NOW) == []


@pytest.mark.parametrize("usage,limits", [([], []), ([series(50, age=1000)], [series(100)]),
                                       ([series(50)], []), ([series(50)], [series(0)])])
def test_missing_stale_or_invalid_memory_is_monitor_failure(usage, limits):
    from scripts.check_production import evaluate_memory
    assert evaluate_memory(usage, limits, NOW)[0]["signal"] == "telemetry"


def test_memory_samples_with_a_gap_do_not_prove_sustained_threshold():
    from scripts.check_production import evaluate_memory
    usage = series(90)
    usage["values"] = [usage["values"][0], usage["values"][-1]]
    assert evaluate_memory([usage], [series(100)], NOW)[0]["signal"] == "telemetry"


@pytest.mark.parametrize("errors,total,alert", [(0,0,False),(4,1000,False),(5,1000,True),
                                              (2,100,True),(1,100,False)])
def test_http_incident_threshold(errors,total,alert):
    from scripts.check_production import evaluate_http
    assert bool(evaluate_http(errors,total)) is alert


def test_invalid_input_is_not_counted_as_server_failure():
    from scripts.check_production import evaluate_operations
    assert evaluate_operations([{"outcome":"invalid_input"}]*20) == []
    assert evaluate_operations([{"outcome":"internal_error"}]*5)[0]["signal"] == "operations"


def test_checker_never_silently_accepts_truncated_logs():
    from scripts.check_production import require_complete_logs, MonitoringError
    with pytest.raises(MonitoringError):
        require_complete_logs({"logs": [], "hasMore": True})


def test_only_confirmed_new_deployment_gets_memory_history_warmup():
    from scripts.check_production import evaluate_memory
    usage = series(50)
    usage["values"] = usage["values"][-3:]
    assert evaluate_memory([usage], [series(100)], NOW, {"one"}) == []
    assert evaluate_memory([usage], [series(100)], NOW)[0]["signal"] == "telemetry"
    assert evaluate_memory([], [], NOW, {"one"})[0]["signal"] == "telemetry"


def test_repeated_boot_during_deployment_still_alerts():
    from scripts.check_production import classify_boots
    deploys = [{"deploy":{"id":"deploy1", "status":"live",
                "createdAt":(NOW-timedelta(minutes=20)).isoformat(),
                "finishedAt":NOW.isoformat()}}]
    boots = [{"timestamp":(NOW-timedelta(minutes=2)).isoformat(), "instance":"one"}]
    assert classify_boots(boots,deploys,NOW) == ([], {"one"})
    boots.append({"timestamp":(NOW-timedelta(minutes=1)).isoformat(), "instance":"two"})
    findings, warming = classify_boots(boots,deploys,NOW)
    assert findings[0]["signal"] == "restart"
    assert warming == {"one"}


def test_restart_long_after_deploy_is_not_planned():
    from scripts.check_production import classify_boots
    boot = {"timestamp":NOW.isoformat(),"instance":"one"}
    deploy = {"id":"old", "status":"live", "createdAt":(NOW-timedelta(days=1)).isoformat(),
              "finishedAt":(NOW-timedelta(hours=23)).isoformat()}
    findings, warming = classify_boots([boot],[deploy],NOW)
    assert findings[0]["signal"] == "restart"
    assert warming == set()
