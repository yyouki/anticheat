#!/usr/bin/env python3
"""Summarize local vehicle observations, optionally bound to staging review records."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import stat
import sys
from collections import defaultdict
from typing import Any, Iterable

from staging_review_capture import validate_capture_binding

PREFIX = "[AC-STAGE-VEHICLE] "
MAX_LOG_BYTES = 32 * 1024 * 1024
MAX_TOTAL_LOG_BYTES = 64 * 1024 * 1024
MAX_RECORD_BYTES = 1_048_576
MAX_TOTAL_RECORD_BYTES = 8 * 1024 * 1024
MAX_CAPTURES = 500
MAX_SAMPLES = 100_000
ALLOWED_TRACE_MODELS = frozenset({
    400, 401, 402, 404, 405, 410, 411, 415, 419, 421, 426, 429,
    436, 439, 445, 451, 458, 477, 489, 496, 506, 517, 518, 526,
    527, 533, 541, 546, 547, 550, 555, 560, 562, 565, 566, 567,
    575, 576, 580, 585, 587, 589, 602, 603,
})
REQUIRED_FIELDS = {
    "schema", "actor", "model", "speed_centi_kmh", "ping",
    "packet_loss_centi_pct",
}
ENVIRONMENT_GROUP_FIELDS = (
    "server_commit",
    "staging_artifact_sha256",
    "openmp_version",
    "client_platform",
    "client_build",
    "network_profile",
)
FIELD_NAME = re.compile(r"^[a-z][a-z0-9_]*$")
UNSIGNED_INTEGER = re.compile(r"^(?:0|[1-9][0-9]*)$")
PACKET_LOSS_INTEGER = re.compile(r"^(?:-1|0|[1-9][0-9]*)$")


def _parse_observation(payload: str, line_number: int) -> dict[str, int]:
    """Parse one exact-schema line without echoing untrusted values."""
    fields: dict[str, str] = {}
    for token in payload.split():
        key, separator, value = token.partition("=")
        if not separator or not FIELD_NAME.fullmatch(key) or not value:
            raise ValueError(f"line {line_number}: malformed key/value token")
        if key in fields:
            raise ValueError(f"line {line_number}: duplicate field {key}")
        if key not in REQUIRED_FIELDS:
            raise ValueError(f"line {line_number}: unsupported field {key}")
        fields[key] = value

    missing = REQUIRED_FIELDS.difference(fields)
    if missing:
        raise ValueError(
            f"line {line_number}: missing required field(s): {', '.join(sorted(missing))}"
        )
    if fields["schema"] != "1":
        raise ValueError(f"line {line_number}: unsupported schema")
    if fields["actor"] != "primary":
        raise ValueError(f"line {line_number}: actor must use the primary test role")

    for name in ("model", "speed_centi_kmh", "ping"):
        if not UNSIGNED_INTEGER.fullmatch(fields[name]):
            raise ValueError(f"line {line_number}: {name} must be a non-negative integer")
    if not PACKET_LOSS_INTEGER.fullmatch(fields["packet_loss_centi_pct"]):
        raise ValueError(
            f"line {line_number}: packet_loss_centi_pct must be -1 (unknown) or a non-negative integer"
        )

    model = int(fields["model"], 10)
    speed = int(fields["speed_centi_kmh"], 10)
    ping = int(fields["ping"], 10)
    packet_loss = int(fields["packet_loss_centi_pct"], 10)

    if not 400 <= model <= 611:
        raise ValueError(f"line {line_number}: model is outside the GTA vehicle ID range")
    if model not in ALLOWED_TRACE_MODELS:
        raise ValueError(f"line {line_number}: model is not approved for staging traces")
    if speed > 1_000_000:
        raise ValueError(f"line {line_number}: speed_centi_kmh exceeds the safety bound")
    if ping > 65_535:
        raise ValueError(f"line {line_number}: ping exceeds the valid client ping range")
    if packet_loss != -1 and packet_loss > 10_000:
        raise ValueError(f"line {line_number}: packet loss exceeds 100 percent")

    return {
        "model": model,
        "speed_centi_kmh": speed,
        "ping": ping,
        "packet_loss_centi_pct": packet_loss,
    }


def parse_vehicle_observations(lines: Iterable[str]) -> list[dict[str, int]]:
    """Read only the dedicated vehicle marker; ordinary console output is ignored."""
    observations: list[dict[str, int]] = []
    for line_number, line in enumerate(lines, start=1):
        marker = line.find(PREFIX)
        if marker == -1:
            continue
        observation = _parse_observation(line[marker + len(PREFIX):].strip(), line_number)
        observations.append(observation)
        if len(observations) > MAX_SAMPLES:
            raise ValueError(f"vehicle trace exceeds the {MAX_SAMPLES}-sample limit")
    return observations


def _nearest_rank_percentile(values: list[int], percentile: float) -> int:
    ordered = sorted(values)
    index = max(0, math.ceil(percentile * len(ordered)) - 1)
    return ordered[index]


def _distribution(values: list[int], scale: int = 1) -> dict[str, float | int]:
    return {
        "min": round(min(values) / scale, 2),
        "p50": round(_nearest_rank_percentile(values, 0.50) / scale, 2),
        "p95": round(_nearest_rank_percentile(values, 0.95) / scale, 2),
        "max": round(max(values) / scale, 2),
    }


def _read_regular_file(path: Path, maximum_bytes: int, label: str) -> bytes:
    """Read one bounded regular file and reject symlink inputs."""
    try:
        if path.is_symlink():
            raise ValueError(f"{label} must not be a symlink")
        metadata = path.stat()
        if not stat.S_ISREG(metadata.st_mode):
            raise ValueError(f"{label} must be a regular file")
        if metadata.st_size > maximum_bytes:
            raise ValueError(f"{label} exceeds the {maximum_bytes}-byte limit")
        with path.open("rb") as handle:
            raw = handle.read(maximum_bytes + 1)
    except OSError as error:
        raise ValueError(f"{label} could not be read") from error
    if len(raw) > maximum_bytes:
        raise ValueError(f"{label} exceeds the {maximum_bytes}-byte limit")
    return raw


def _read_log(path: Path) -> tuple[list[dict[str, int]], str]:
    raw = _read_regular_file(path, MAX_LOG_BYTES, "capture log")
    digest = hashlib.sha256(raw).hexdigest()
    text = raw.decode("utf-8", errors="replace")
    return parse_vehicle_observations(text.splitlines()), digest


def _read_review_record(path: Path) -> dict[str, Any]:
    raw = _read_regular_file(path, MAX_RECORD_BYTES, "review record")
    def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("review record contains duplicate JSON keys")
            result[key] = value
        return result

    try:
        data = json.loads(raw.decode("utf-8"), object_pairs_hook=reject_duplicate_keys)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        raise ValueError("review record could not be read as JSON") from error
    if not isinstance(data, dict):
        raise ValueError("review record root must be an object")
    return data


def _load_bound_traces(
    log_paths: list[Path],
    record_paths: list[Path],
) -> tuple[list[dict[str, int]], dict[str, Any]]:
    """Verify one schema-v2 review record against every exact source capture."""
    if len(log_paths) != len(record_paths):
        raise ValueError("provide exactly one --record for each --log, in matching order")
    if len(log_paths) > MAX_CAPTURES:
        raise ValueError(f"capture set exceeds the {MAX_CAPTURES}-run limit")

    observations: list[dict[str, int]] = []
    run_ids: set[str] = set()
    capture_digests: set[str] = set()
    common_environment: dict[str, str] | None = None
    total_log_bytes = 0
    total_record_bytes = 0
    source_runs: list[dict[str, Any]] = []

    for log_path, record_path in zip(log_paths, record_paths, strict=True):
        try:
            total_log_bytes += log_path.stat().st_size
            total_record_bytes += record_path.stat().st_size
        except OSError as error:
            raise ValueError("capture or review record could not be read") from error
        if total_log_bytes > MAX_TOTAL_LOG_BYTES:
            raise ValueError(f"combined logs exceed the {MAX_TOTAL_LOG_BYTES}-byte limit")
        if total_record_bytes > MAX_TOTAL_RECORD_BYTES:
            raise ValueError(f"combined review records exceed the {MAX_TOTAL_RECORD_BYTES}-byte limit")
        record = _read_review_record(record_path)
        environment = record.get("environment")
        if not isinstance(environment, dict):
            raise ValueError("review record environment must be an object")

        binding, _ = validate_capture_binding(record, log_path)
        if binding.get("status") != "valid" or binding.get("binding_verified") is not True:
            raise ValueError("a review record failed exact capture binding or staging log validation")

        digest = binding.get("capture_sha256")
        run_id = binding.get("run_id")
        if not isinstance(digest, str) or not isinstance(run_id, str):
            raise ValueError("validated review record is missing its run ID or capture digest")
        if digest in capture_digests:
            raise ValueError("duplicate capture digest detected; each input must be a distinct run")
        if run_id in run_ids:
            raise ValueError("duplicate review run ID detected")
        capture_digests.add(digest)
        run_ids.add(run_id)

        # Re-read the exact bytes used for telemetry parsing and compare the digest.
        # This guards against a file changing between the binding check and parsing.
        samples, parsed_digest = _read_log(log_path)
        if parsed_digest != digest:
            raise ValueError("capture file changed while the bound trace report was being built")
        if not samples:
            raise ValueError("a bound capture contains no vehicle telemetry observations")

        model_ids = {sample["model"] for sample in samples}
        if len(model_ids) != 1:
            raise ValueError("each bound capture must contain exactly one approved vehicle model")

        observation = next(
            (
                item for item in record.get("observations", [])
                if isinstance(item, dict) and item.get("scenario_id") == "vehicle_enter_drive_exit"
            ),
            None,
        )
        if not isinstance(observation, dict) or observation.get("result") != "clean":
            raise ValueError("vehicle_enter_drive_exit must be recorded as clean in each bound review")

        environment_group = {
            field: environment.get(field)
            for field in ENVIRONMENT_GROUP_FIELDS
        }
        if common_environment is None:
            common_environment = environment_group
        elif environment_group != common_environment:
            raise ValueError(
                "bound captures have mismatched server, artifact, open.mp, client build, or network metadata"
            )

        observations.extend(samples)
        if len(observations) > MAX_SAMPLES:
            raise ValueError(f"combined traces exceed the {MAX_SAMPLES}-sample limit")
        source_runs.append({
            "run_id": run_id,
            "capture_sha256": digest,
            "model_id": next(iter(model_ids)),
            "sample_count": len(samples),
        })

    return observations, {
        "binding_status": "verified",
        "review_record_count": len(record_paths),
        "environment": common_environment,
        "source_runs": source_runs,
    }


def _load_unbound_traces(log_paths: list[Path]) -> tuple[list[dict[str, int]], dict[str, Any]]:
    """Load exploratory traces without claiming that review records were checked."""
    observations: list[dict[str, int]] = []
    capture_digests: set[str] = set()
    source_runs: list[dict[str, Any]] = []

    total_log_bytes = 0
    for index, log_path in enumerate(log_paths, start=1):
        try:
            total_log_bytes += log_path.stat().st_size
        except OSError as error:
            raise ValueError("capture log could not be read") from error
        if total_log_bytes > MAX_TOTAL_LOG_BYTES:
            raise ValueError(f"combined logs exceed the {MAX_TOTAL_LOG_BYTES}-byte limit")

        samples, digest = _read_log(log_path)
        if digest in capture_digests:
            raise ValueError("duplicate capture file detected; do not count one run more than once")
        capture_digests.add(digest)
        if not samples:
            continue
        model_ids = {sample["model"] for sample in samples}
        if len(model_ids) != 1:
            raise ValueError("each input capture must contain exactly one approved vehicle model")
        observations.extend(samples)
        if len(observations) > MAX_SAMPLES:
            raise ValueError(f"combined traces exceed the {MAX_SAMPLES}-sample limit")
        source_runs.append({
            "source_index": index,
            "capture_sha256": digest,
            "model_id": next(iter(model_ids)),
            "sample_count": len(samples),
        })

    return observations, {
        "binding_status": "not_provided",
        "review_record_count": 0,
        "environment": None,
        "source_runs": source_runs,
    }


def build_report(
    observations: list[dict[str, int]],
    provenance: dict[str, Any] | None = None,
) -> dict[str, object]:
    grouped: dict[int, list[dict[str, int]]] = defaultdict(list)
    for observation in observations:
        grouped[observation["model"]].append(observation)

    models: dict[str, object] = {}
    for model in sorted(grouped):
        samples = grouped[model]
        known_loss = [
            sample["packet_loss_centi_pct"]
            for sample in samples
            if sample["packet_loss_centi_pct"] >= 0
        ]
        models[str(model)] = {
            "sample_count": len(samples),
            "speed_kmh": _distribution(
                [sample["speed_centi_kmh"] for sample in samples], scale=100
            ),
            "ping_ms": _distribution([sample["ping"] for sample in samples]),
            "packet_loss_known_samples": len(known_loss),
            "packet_loss_percent": _distribution(known_loss, scale=100) if known_loss else None,
        }

    trace_provenance = provenance or {
        "binding_status": "not_provided",
        "review_record_count": 0,
        "environment": None,
        "source_runs": [],
    }
    binding_verified = trace_provenance["binding_status"] == "verified"
    return {
        "report_schema_version": 2,
        "report_type": "openmp_vehicle_telemetry_summary",
        "status": "observations_found" if observations else "empty",
        "validation_scope": "descriptive_server_side_staging_observations",
        "sample_count": len(observations),
        "models": models,
        "provenance": trace_provenance,
        "runtime_validation": {
            "capture_file_binding_verified": binding_verified,
            "log_origin_authenticated": False,
            "operator_scenario_execution_verified": False,
            "detector_accuracy_verified": False,
            "safe_speed_envelope_established": False,
            "production_ready": False,
        },
        "limitations": [
            "Percentiles describe the supplied captures; they are not safe speed limits.",
            "Observations do not establish whether an action is legitimate or anomalous.",
            "A verified binding checks exact file bytes and the review schema, not log origin or actual scenario execution.",
            "Packet loss is unknown when no fresh host-supplied measurement was available.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Summarize local open.mp staging vehicle observations."
    )
    parser.add_argument(
        "--log",
        required=True,
        action="append",
        type=Path,
        help="local server console log; repeat for additional model captures",
    )
    parser.add_argument(
        "--record",
        action="append",
        type=Path,
        help="matching schema-v2 review JSON; repeat once per --log in the same order to verify SHA-256 bindings",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="print machine-readable output (descriptive only; not a detector verdict)",
    )
    args = parser.parse_args()

    try:
        if args.record:
            observations, provenance = _load_bound_traces(args.log, args.record)
        else:
            observations, provenance = _load_unbound_traces(args.log)
    except (OSError, UnicodeError, ValueError) as error:
        print(f"Could not validate vehicle trace: {error}", file=sys.stderr)
        return 2

    report = build_report(observations, provenance)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    elif not observations:
        print("No vehicle telemetry observations found in the supplied logs.")
        print("Start /acstagelogbegin, drive an approved staging road car, then end the capture.")
        if provenance["binding_status"] == "not_provided":
            print("No review records were supplied; capture bindings were not checked.")
    else:
        print(
            f"Vehicle observations: {len(observations)} across "
            f"{len(report['models'])} model(s)"
        )
        for model, summary in report["models"].items():
            speed = summary["speed_kmh"]
            ping = summary["ping_ms"]
            print(
                f"  model {model}: n={summary['sample_count']}; "
                f"speed km/h min/p50/p95/max="
                f"{speed['min']}/{speed['p50']}/{speed['p95']}/{speed['max']}; "
                f"ping ms min/p50/p95/max="
                f"{ping['min']}/{ping['p50']}/{ping['p95']}/{ping['max']}"
            )
        print(f"Capture binding: {provenance['binding_status']}.")
        print("Scope: descriptive observations only; no safe envelope or detector verdict.")
    return 0 if observations else 1


if __name__ == "__main__":
    raise SystemExit(main())
