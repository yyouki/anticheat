#!/usr/bin/env python3
"""Validate privacy-safe manual staging observations without certifying detector quality."""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime
import json
from pathlib import Path
import re
import sys
from typing import Any

SCENARIO_PATH = Path(__file__).with_name("staging_review_scenarios.json")
RUN_ID_PATTERN = re.compile(r"^[a-z][a-z0-9-]{2,31}$")
COMMIT_PATTERN = re.compile(r"^[0-9a-f]{40}$")
DIGEST_PATTERN = re.compile(r"^[0-9a-f]{64}$")
CLIENT_BUILD_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9._+-]{0,31}$")
OPENMP_VERSION_PATTERN = re.compile(r"^v[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$")

CLIENT_PLATFORMS = {"android", "windows", "linux", "macos", "other"}
NETWORK_PROFILES = {"stable", "high_ping", "jitter", "packet_loss", "low_fps"}
RESULTS = {"clean", "evidence", "blocked", "not_run"}
REVIEW_DECISIONS = {
    "not_applicable",
    "pending",
    "confirmed_false_positive",
    "rejected_false_positive",
    "inconclusive",
}
EVIDENCE_CATEGORIES = {"movement", "vehicle", "combat", "integrity", "state"}
BLOCK_REASONS = {
    "second_client_unavailable",
    "client_build_unavailable",
    "staging_server_unavailable",
    "network_profile_unavailable",
    "scenario_not_supported",
    "other",
}


def _load_scenarios() -> tuple[dict[str, dict[str, Any]], list[str]]:
    try:
        data = json.loads(SCENARIO_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}, ["scenario manifest could not be loaded"]

    if not isinstance(data, dict) or type(data.get("schema_version")) is not int or data.get("schema_version") != 1:
        return {}, ["scenario manifest schema is invalid"]
    scenarios = data.get("scenarios")
    if not isinstance(scenarios, list):
        return {}, ["scenario manifest list is invalid"]

    result: dict[str, dict[str, Any]] = {}
    for item in scenarios:
        if not isinstance(item, dict) or not isinstance(item.get("id"), str):
            return {}, ["scenario manifest contains an invalid entry"]
        if item["id"] in result:
            return {}, ["scenario manifest contains a duplicate ID"]
        result[item["id"]] = item
    if not result:
        return {}, ["scenario manifest is empty"]
    return result, []


def _exact_keys(value: dict[str, Any], required: set[str], errors: list[str], label: str) -> None:
    if set(value) != required:
        errors.append(f"{label} must contain exactly the documented fields")


def _valid_timestamp(value: Any) -> bool:
    if not isinstance(value, str) or not value:
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None and parsed.utcoffset() is not None


def _invalid_payload(errors: list[str]) -> dict[str, Any]:
    return {
        "record_status": "invalid",
        "errors": errors,
        "claims": {
            "false_positive_free_certified": False,
            "independently_verified": False,
            "production_ready": False,
        },
    }


def validate_review_record(data: Any) -> dict[str, Any]:
    """Validate one operator-authored run record and return a non-certifying summary."""
    scenarios, errors = _load_scenarios()
    if errors:
        return _invalid_payload(errors)
    if not isinstance(data, dict):
        return _invalid_payload(["record root must be an object"])

    _exact_keys(data, {"schema_version", "run_id", "environment", "observations"}, errors, "record")
    if type(data.get("schema_version")) is not int or data.get("schema_version") != 2:
        errors.append("schema_version must equal 2")

    run_id = data.get("run_id")
    if not isinstance(run_id, str) or not RUN_ID_PATTERN.fullmatch(run_id):
        errors.append("run_id must be a short non-identifying label")

    environment = data.get("environment")
    if not isinstance(environment, dict):
        errors.append("environment must be an object")
        environment = {}
    else:
        _exact_keys(
            environment,
            {
                "server_commit",
                "staging_artifact_sha256",
                "capture_sha256",
                "openmp_version",
                "client_platform",
                "client_build",
                "network_profile",
                "started_at",
            },
            errors,
            "environment",
        )

    if not isinstance(environment.get("server_commit"), str) or not COMMIT_PATTERN.fullmatch(
        environment.get("server_commit", "")
    ):
        errors.append("environment.server_commit must be a 40-character commit SHA")
    if not isinstance(environment.get("staging_artifact_sha256"), str) or not DIGEST_PATTERN.fullmatch(
        environment.get("staging_artifact_sha256", "")
    ):
        errors.append("environment.staging_artifact_sha256 must be a 64-character SHA-256 digest")
    if not isinstance(environment.get("capture_sha256"), str) or not DIGEST_PATTERN.fullmatch(
        environment.get("capture_sha256", "")
    ):
        errors.append("environment.capture_sha256 must be a 64-character SHA-256 digest")
    if not isinstance(environment.get("openmp_version"), str) or not OPENMP_VERSION_PATTERN.fullmatch(
        environment.get("openmp_version", "")
    ):
        errors.append("environment.openmp_version must use the vX.Y.Z.BUILD form")
    client_platform = environment.get("client_platform")
    if not isinstance(client_platform, str) or client_platform not in CLIENT_PLATFORMS:
        errors.append("environment.client_platform is unsupported")
    if not isinstance(environment.get("client_build"), str) or not CLIENT_BUILD_PATTERN.fullmatch(
        environment.get("client_build", "")
    ):
        errors.append("environment.client_build must be a short build label, not a device identifier")
    network_profile = environment.get("network_profile")
    if not isinstance(network_profile, str) or network_profile not in NETWORK_PROFILES:
        errors.append("environment.network_profile is unsupported")
    if not _valid_timestamp(environment.get("started_at")):
        errors.append("environment.started_at must be an ISO-8601 timestamp with a timezone")

    observations = data.get("observations")
    if not isinstance(observations, list):
        errors.append("observations must be an array")
        observations = []

    seen: set[str] = set()
    result_counts: Counter[str] = Counter()
    review_counts: Counter[str] = Counter()
    evidence_counts: Counter[str] = Counter()

    for observation in observations:
        if not isinstance(observation, dict):
            errors.append("each observation must be an object")
            continue
        _exact_keys(
            observation,
            {"scenario_id", "result", "evidence_categories", "review_decision", "block_reason", "secondary_client_connected"},
            errors,
            "observation",
        )

        scenario_id = observation.get("scenario_id")
        if not isinstance(scenario_id, str) or scenario_id not in scenarios:
            errors.append("observation contains an unknown scenario_id")
            continue
        if scenario_id in seen:
            errors.append("observation contains a duplicate scenario_id")
            continue
        seen.add(scenario_id)

        result = observation.get("result")
        decision = observation.get("review_decision")
        categories = observation.get("evidence_categories")
        block_reason = observation.get("block_reason")
        secondary_connected = observation.get("secondary_client_connected")

        if not isinstance(result, str) or result not in RESULTS:
            errors.append(f"{scenario_id}: result is unsupported")
            continue
        if not isinstance(decision, str) or decision not in REVIEW_DECISIONS:
            errors.append(f"{scenario_id}: review_decision is unsupported")
            continue
        if not isinstance(categories, list) or any(
            not isinstance(category, str) or category not in EVIDENCE_CATEGORIES for category in categories
        ):
            errors.append(f"{scenario_id}: evidence_categories contains an unsupported value")
            continue
        if len(set(categories)) != len(categories):
            errors.append(f"{scenario_id}: evidence_categories contains duplicates")
        if not isinstance(secondary_connected, bool):
            errors.append(f"{scenario_id}: secondary_client_connected must be boolean")

        result_counts[result] += 1
        review_counts[decision] += 1
        evidence_counts.update(categories)

        if result == "clean":
            if categories or decision != "not_applicable" or block_reason is not None:
                errors.append(f"{scenario_id}: clean results must have no evidence, review or block reason")
        elif result == "evidence":
            if not categories:
                errors.append(f"{scenario_id}: evidence results must name at least one category")
            if decision not in {"pending", "confirmed_false_positive", "rejected_false_positive", "inconclusive"}:
                errors.append(f"{scenario_id}: evidence requires an explicit human review decision")
            if block_reason is not None:
                errors.append(f"{scenario_id}: evidence results cannot have a block reason")
        elif result == "blocked":
            if (
                categories
                or decision != "not_applicable"
                or not isinstance(block_reason, str)
                or block_reason not in BLOCK_REASONS
            ):
                errors.append(f"{scenario_id}: blocked results require a controlled block reason and no evidence")
        elif result == "not_run":
            if categories or decision != "not_applicable" or block_reason is not None:
                errors.append(f"{scenario_id}: not_run results cannot contain evidence or review data")

        if scenarios[scenario_id].get("requires_secondary_client") and result in {"clean", "evidence"}:
            if secondary_connected is not True:
                errors.append(f"{scenario_id}: an executed spectate scenario requires a connected secondary client")

    missing = sorted(set(scenarios).difference(seen))
    if not observations:
        errors.append("at least one observation is required")

    if errors:
        return _invalid_payload(errors)

    scenario_execution_complete = (
        not missing and all(result_counts[name] == 0 for name in ("blocked", "not_run"))
    )
    evidence_review_complete = (
        review_counts["pending"] == 0 and review_counts["inconclusive"] == 0
    )
    confirmed_false_positives = review_counts["confirmed_false_positive"]
    if confirmed_false_positives:
        evaluation_state = "confirmed_false_positive_present"
    elif not scenario_execution_complete or not evidence_review_complete:
        evaluation_state = "incomplete_or_pending"
    else:
        evaluation_state = "observations_reviewed"

    return {
        "record_status": "valid",
        "run_id": run_id,
        "capture_sha256": environment["capture_sha256"],
        "evaluation_state": evaluation_state,
        "scenario_records_complete": not missing,
        "scenario_execution_complete": scenario_execution_complete,
        "evidence_review_complete": evidence_review_complete,
        "missing_scenario_ids": missing,
        "scenario_counts": {name: result_counts[name] for name in sorted(RESULTS)},
        "review_counts": {name: review_counts[name] for name in sorted(REVIEW_DECISIONS)},
        "evidence_category_counts": {name: evidence_counts[name] for name in sorted(EVIDENCE_CATEGORIES)},
        "confirmed_false_positive_count": confirmed_false_positives,
        "claims": {
            "false_positive_free_certified": False,
            "independently_verified": False,
            "production_ready": False,
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate one privacy-safe manual open.mp staging review record."
    )
    parser.add_argument("--record", required=True, type=Path, help="completed staging review JSON record")
    args = parser.parse_args(argv)

    try:
        with args.record.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        print(json.dumps(_invalid_payload(["record file could not be read as JSON"]), indent=2, sort_keys=True))
        return 1

    report = validate_review_record(data)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["record_status"] == "valid" else 1


if __name__ == "__main__":
    raise SystemExit(main())
