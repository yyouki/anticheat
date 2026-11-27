#!/usr/bin/env python3
"""Validate privacy-safe interactive acceptance logs from the open.mp staging harness."""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
import re
import sys
from typing import Iterable

PREFIX = "[AC-STAGE-EVENT] "
ALLOWED_EVENTS = {
    "run_begin", "run_end", "run_abort",
    "interior_enter", "interior_exit", "interior_callback",
    "world_enter", "world_exit",
    "spectate_start", "spectate_stop",
    "spectate_state_enter", "spectate_state_exit",
    "evidence", "review_marker",
}
ALLOWED_FIELDS = {
    "schema", "event", "actor", "from", "to", "old", "new",
    "target", "category", "points", "ping", "strikes", "reason",
}
FIELD_NAME = re.compile(r"^[a-z][a-z0-9_]*$")
INTEGER_FIELDS = {"from", "to", "old", "new", "points", "ping", "strikes"}


@dataclass(frozen=True)
class StagingReport:
    passed: bool
    event_counts: dict[str, int]
    evidence_count: int
    review_marker_count: int
    errors: tuple[str, ...]


def _parse_record(payload: str, line_number: int) -> dict[str, str]:
    fields: dict[str, str] = {}
    for token in payload.split():
        key, separator, value = token.partition("=")
        if not separator or not FIELD_NAME.fullmatch(key) or not value:
            raise ValueError(f"line {line_number}: malformed key/value token")
        if key in fields:
            raise ValueError(f"line {line_number}: duplicate field {key}")
        if key not in ALLOWED_FIELDS:
            raise ValueError(f"line {line_number}: unsupported field {key}")
        fields[key] = value

    if fields.get("schema") != "1":
        raise ValueError(f"line {line_number}: unsupported or missing schema")
    if fields.get("actor") != "primary":
        raise ValueError(f"line {line_number}: actor must use the primary test role")
    event = fields.get("event")
    if event not in ALLOWED_EVENTS:
        raise ValueError(f"line {line_number}: unsupported event {event!r}")

    for name in INTEGER_FIELDS.intersection(fields):
        try:
            int(fields[name], 10)
        except ValueError as error:
            raise ValueError(f"line {line_number}: {name} must be an integer") from error
    return fields


def parse_staging_log(lines: Iterable[str]) -> StagingReport:
    """Parse one bounded acceptance capture and evaluate its required observations."""
    errors: list[str] = []
    events: list[dict[str, str]] = []
    capture_started = False
    capture_ended = False
    capture_open = False
    capture_count = 0

    for line_number, line in enumerate(lines, start=1):
        marker = line.find(PREFIX)
        if marker == -1:
            continue
        payload = line[marker + len(PREFIX):].strip()
        try:
            record = _parse_record(payload, line_number)
        except ValueError as error:
            if capture_open or not capture_started:
                errors.append(str(error))
            continue

        name = record["event"]
        if name == "run_begin":
            capture_count += 1
            if capture_count > 1:
                errors.append("multiple acceptance captures found; provide one capture per report")
                continue
            capture_started = True
            capture_open = True
            events.append(record)
            continue

        if not capture_open:
            continue

        events.append(record)
        if name == "run_end":
            capture_ended = True
            capture_open = False
        elif name == "run_abort":
            errors.append("capture aborted before normal completion")

    if not capture_started:
        errors.append("no run_begin marker found")
    if capture_open or (capture_started and not capture_ended):
        errors.append("capture is incomplete; run_end marker is missing")
    if capture_count != 1:
        errors.append("exactly one acceptance capture is required")

    counts = Counter(event["event"] for event in events)
    required_once = (
        "interior_enter", "interior_exit", "world_enter", "world_exit",
        "spectate_start", "spectate_stop", "spectate_state_enter", "spectate_state_exit",
    )
    for name in required_once:
        if counts[name] != 1:
            errors.append(f"expected exactly one {name} event; found {counts[name]}")

    interior_callbacks = [event for event in events if event["event"] == "interior_callback"]
    if len(interior_callbacks) != 2:
        errors.append(f"expected two interior_callback observations; found {len(interior_callbacks)}")
    else:
        first, second = interior_callbacks
        if int(first.get("new", "-1")) != 17 or int(first.get("old", "-1")) == 17:
            errors.append("first interior callback must enter interior 17")
        if int(second.get("old", "-1")) != 17 or int(second.get("new", "-1")) == 17:
            errors.append("second interior callback must leave interior 17")

    by_name = {
        name: [index for index, event in enumerate(events) if event["event"] == name]
        for name in ALLOWED_EVENTS
    }
    for earlier, later in (
        ("interior_enter", "interior_exit"),
        ("world_enter", "world_exit"),
        ("spectate_start", "spectate_stop"),
        ("spectate_state_enter", "spectate_state_exit"),
    ):
        if by_name[earlier] and by_name[later] and by_name[earlier][0] >= by_name[later][0]:
            errors.append(f"{earlier} must occur before {later}")

    for name, field, expected in (
        ("interior_enter", "to", 17),
        ("interior_exit", "from", 17),
        ("world_enter", "to", 9000),
        ("world_exit", "from", 9000),
    ):
        matching = [event for event in events if event["event"] == name]
        if matching:
            try:
                actual = int(matching[0][field], 10)
            except (KeyError, ValueError):
                errors.append(f"{name} must include an integer {field} field")
            else:
                if actual != expected:
                    errors.append(f"{name} expected {field}={expected}, found {actual}")

    spectate_starts = [event for event in events if event["event"] == "spectate_start"]
    if spectate_starts and spectate_starts[0].get("target") != "secondary":
        errors.append("spectate_start must use target=secondary, never a player ID")

    evidence_count = counts["evidence"]
    review_marker_count = counts["review_marker"]
    if evidence_count:
        errors.append(f"{evidence_count} evidence event(s) occurred during the acceptance window")
    if review_marker_count:
        errors.append(f"{review_marker_count} review marker event(s) occurred during the acceptance window")

    return StagingReport(
        passed=not errors,
        event_counts=dict(sorted(counts.items())),
        evidence_count=evidence_count,
        review_marker_count=review_marker_count,
        errors=tuple(errors),
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate one privacy-safe open.mp staging acceptance log."
    )
    parser.add_argument("--log", required=True, type=Path, help="server console log containing one capture")
    args = parser.parse_args()

    try:
        with args.log.open("r", encoding="utf-8", errors="replace") as handle:
            report = parse_staging_log(handle)
    except OSError as error:
        print(f"Could not read staging log: {error}", file=sys.stderr)
        return 2

    print(f"Staging acceptance report: {'PASS' if report.passed else 'FAIL'}")
    print(
        f"Observed events: {sum(report.event_counts.values())}; "
        f"evidence: {report.evidence_count}; review markers: {report.review_marker_count}"
    )
    for name, count in report.event_counts.items():
        print(f"  {name}: {count}")
    for error in report.errors:
        print(f"ERROR: {error}")
    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
