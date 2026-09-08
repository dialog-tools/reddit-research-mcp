"""Fail the release gate when a completed synthetic soak is not bounded."""
import argparse
import json
from pathlib import Path
import statistics
import sys


def analyze(samples, minimum_seconds=7200):
    reasons = []
    if not samples or samples[-1]["elapsed"] < minimum_seconds:
        return {"passed":False, "reasons":["Required soak duration not completed"]}
    warm = [s for s in samples if s["elapsed"] >= 600]
    if len(warm) < 20:
        return {"passed":False, "reasons":["Too few post-warmup samples"]}
    if any(s["sessions"] != 0 for s in samples):
        reasons.append("Sessions retained after cleanup")
    width = max(1,len(warm)//3)
    for field in ["tasks","threads","file_descriptors"]:
        values = [s[field] for s in warm]
        if max(values)-min(values) > 2 or statistics.mean(values[-width:])-statistics.mean(values[:width]) > 1:
            reasons.append(f"Unbounded {field}")
    hours = [s["elapsed"]/3600 for s in warm]
    mib = [s["rss_bytes"]/1048576 for s in warm]
    slope, _ = statistics.linear_regression(hours,mib)
    if slope >= 10:
        reasons.append("RSS growth reached 10 MiB/hour")
    return {"passed":not reasons, "reasons":reasons, "duration_seconds":samples[-1]["elapsed"],
            "batches":len(samples), "rss_mib_min":round(min(mib),2), "rss_mib_max":round(max(mib),2),
            "rss_mib_per_hour":round(slope,3),
            "post_warmup_counts":{field:sorted({s[field] for s in warm}) for field in ["sessions","tasks","threads","file_descriptors"]}}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("file",type=Path)
    args = parser.parse_args()
    samples = []
    for line in args.file.read_text().splitlines():
        try:
            record = json.loads(line)
        except ValueError:
            continue
        if isinstance(record,dict) and "batch" in record:
            samples.append(record)
    result = analyze(samples)
    print(json.dumps(result,indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
