#!/usr/bin/env python3
"""Summarize privacy-safe vehicle observations from a local open.mp staging log."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import re
import sys
from collections import defaultdict
from typing import Iterable

PREFIX = "[AC-STAGE-VEHICLE] "
MAX_LOG_BYTES = 32 * 1024 * 1024
MAX_SAMPLES = 100_000
REQUIRED_FIELDS = {
    "schema", "actor", "model", "speed_centi_kmh", "ping",
    "packet_loss_centi_pct",
}
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


def build_report(observations: list[dict[str, int]]) -> dict[str, object]:
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

    return {
        "report_schema_version": 1,
        "report_type": "openmp_vehicle_telemetry_summary",
        "status": "observations_found" if observations else "empty",
        "validation_scope": "descriptive_server_side_staging_observations",
        "sample_count": len(observations),
        "models": models,
        "runtime_validation": {
            "log_origin_authenticated": False,
            "detector_accuracy_verified": False,
            "safe_speed_envelope_established": False,
            "production_ready": False,
        },
        "limitations": [
            "Percentiles describe this capture only; they are not safe speed limits.",
            "Observations do not establish whether an action is legitimate or anomalous.",
            "Packet loss is -1 when no fresh host-supplied measurement was available.",
            "The report cannot authenticate log origin or prove that the operator ran the stated scenario.",
        ],
    }


def _read_log(path: Path) -> list[dict[str, int]]:
    if path.is_symlink():
        raise ValueError("symlink log inputs are not accepted")
    if not path.is_file():
        raise ValueError("log input must be a regular file")
    if path.stat().st_size > MAX_LOG_BYTES:
        raise ValueError(f"log exceeds the {MAX_LOG_BYTES}-byte limit")
    with path.open("r", encoding="utf-8", errors="strict") as handle:
        return parse_vehicle_observations(handle)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Summarize local privacy-safe open.mp staging vehicle observations."
    )
    parser.add_argument("--log", required=True, type=Path, help="local server console log")
    parser.add_argument(
        "--json",
        action="store_true",
        help="print machine-readable output (descriptive only; not a detector verdict)",
    )
    args = parser.parse_args()

    try:
        observations = _read_log(args.log)
    except (OSError, UnicodeError, ValueError) as error:
        print(f"Could not validate vehicle trace: {error}", file=sys.stderr)
        return 2

    report = build_report(observations)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    elif not observations:
        print("No vehicle telemetry observations found in the supplied log.")
        print("Start /acstagelogbegin, drive an approved staging road car, then end the capture.")
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
        print("Scope: descriptive observations only; no safe envelope or detector verdict.")
    return 0 if observations else 1


if __name__ == "__main__":
    raise SystemExit(main())
