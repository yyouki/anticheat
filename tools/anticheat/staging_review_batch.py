#!/usr/bin/env python3
"""Aggregate validated staging review records without estimating detector accuracy."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import sys
from typing import Any

from staging_review import validate_review_record

MAX_RECORDS = 500
GROUP_FIELDS = (
    "server_commit",
    "staging_artifact_sha256",
    "openmp_version",
    "client_platform",
    "client_build",
    "network_profile",
)
RESULTS = ("clean", "evidence", "blocked", "not_run")
DECISIONS = (
    "not_applicable",
    "pending",
    "confirmed_false_positive",
    "rejected_false_positive",
    "inconclusive",
)
CATEGORIES = ("movement", "vehicle", "combat", "integrity", "state")


def _empty_group(environment: dict[str, Any]) -> dict[str, Any]:
    return {
        "environment": {field: environment[field] for field in GROUP_FIELDS},
        "run_count": 0,
        "scenario_result_counts": {
            scenario: Counter({result: 0 for result in RESULTS}) for scenario in ()
        },
        "result_counts": Counter({result: 0 for result in RESULTS}),
        "review_decision_counts": Counter({decision: 0 for decision in DECISIONS}),
        "evidence_category_counts": Counter({category: 0 for category in CATEGORIES}),
        "confirmed_false_positive_count": 0,
    }


def aggregate_records(records: list[Any]) -> dict[str, Any]:
    """Validate and aggregate records by exact server/client/network build tuple."""
    if not isinstance(records, list) or not records:
        return {"status": "invalid", "errors": ["at least one record is required"]}

    if len(records) > MAX_RECORDS:
        return {"status": "invalid", "errors": [f"record count exceeds the limit of {MAX_RECORDS}"]}

    errors: list[str] = []
    valid: list[tuple[dict[str, Any], dict[str, Any]]] = []
    seen_run_ids: set[str] = set()

    for index, record in enumerate(records, start=1):
        report = validate_review_record(record)
        if report["record_status"] != "valid":
            errors.append(f"record {index} failed individual validation")
            continue
        run_id = report["run_id"]
        if run_id in seen_run_ids:
            errors.append("duplicate run_id detected")
            continue
        seen_run_ids.add(run_id)
        valid.append((record, report))

    if errors:
        return {
            "status": "invalid",
            "record_count": len(records),
            "valid_record_count": len(valid),
            "errors": errors,
            "claims": {
                "false_positive_rate_estimated": False,
                "false_positive_free_certified": False,
                "independently_verified": False,
                "production_ready": False,
            },
        }

    groups: dict[tuple[str, ...], dict[str, Any]] = {}
    for record, report in valid:
        environment = record["environment"]
        key = tuple(environment[field] for field in GROUP_FIELDS)
        group = groups.setdefault(key, _empty_group(environment))
        group["run_count"] += 1
        group["confirmed_false_positive_count"] += report["confirmed_false_positive_count"]
        for name, count in report["scenario_counts"].items():
            group["result_counts"][name] += count
        for name, count in report["review_counts"].items():
            group["review_decision_counts"][name] += count
        for name, count in report["evidence_category_counts"].items():
            group["evidence_category_counts"][name] += count

    rendered_groups = []
    for key in sorted(groups):
        group = groups[key]
        rendered_groups.append({
            "environment": group["environment"],
            "run_count": group["run_count"],
            "result_counts": dict(sorted(group["result_counts"].items())),
            "review_decision_counts": dict(sorted(group["review_decision_counts"].items())),
            "evidence_category_counts": dict(sorted(group["evidence_category_counts"].items())),
            "confirmed_false_positive_count": group["confirmed_false_positive_count"],
        })

    totals = {
        "result_counts": Counter({name: 0 for name in RESULTS}),
        "review_decision_counts": Counter({name: 0 for name in DECISIONS}),
        "evidence_category_counts": Counter({name: 0 for name in CATEGORIES}),
        "confirmed_false_positive_count": 0,
    }
    for group in groups.values():
        for name, count in group["result_counts"].items():
            totals["result_counts"][name] += count
        for name, count in group["review_decision_counts"].items():
            totals["review_decision_counts"][name] += count
        for name, count in group["evidence_category_counts"].items():
            totals["evidence_category_counts"][name] += count
        totals["confirmed_false_positive_count"] += group["confirmed_false_positive_count"]

    return {
        "status": "valid",
        "record_count": len(records),
        "group_count": len(groups),
        "groups": rendered_groups,
        "totals": {
            "result_counts": dict(sorted(totals["result_counts"].items())),
            "review_decision_counts": dict(sorted(totals["review_decision_counts"].items())),
            "evidence_category_counts": dict(sorted(totals["evidence_category_counts"].items())),
            "confirmed_false_positive_count": totals["confirmed_false_positive_count"],
        },
        "interpretation": {
            "counts_are_observations_not_rates": True,
            "records_are_operator_authored_and_not_independently_verified": True,
            "false_positive_rate_estimated": False,
        },
        "claims": {
            "false_positive_free_certified": False,
            "independently_verified": False,
            "production_ready": False,
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Aggregate validated staging review JSON files by exact build and network profile."
    )
    parser.add_argument("--records-dir", required=True, type=Path, help="directory containing review JSON records")
    args = parser.parse_args(argv)

    try:
        paths = sorted(path for path in args.records_dir.glob("*.json") if path.is_file())
    except OSError:
        paths = []

    if not paths:
        report = {"status": "invalid", "errors": ["no review JSON files found"]}
        print(json.dumps(report, indent=2, sort_keys=True))
        return 1
    if len(paths) > MAX_RECORDS:
        report = {"status": "invalid", "errors": [f"record count exceeds the limit of {MAX_RECORDS}"]}
        print(json.dumps(report, indent=2, sort_keys=True))
        return 1

    records: list[Any] = []
    for path in paths:
        try:
            with path.open("r", encoding="utf-8") as handle:
                records.append(json.load(handle))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            records.append(None)

    report = aggregate_records(records)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "valid" else 1


if __name__ == "__main__":
    raise SystemExit(main())
