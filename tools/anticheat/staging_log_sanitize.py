#!/usr/bin/env python3
"""Export only validated pseudonymous staging records from a local console log."""

from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import stat
import sys

from staging_report import PREFIX as EVENT_PREFIX
from staging_report import _parse_record, parse_staging_log
from vehicle_trace_report import PREFIX as VEHICLE_PREFIX
from vehicle_trace_report import parse_vehicle_observations

MAX_SOURCE_BYTES = 32 * 1024 * 1024
MAX_EXPORT_BYTES = 8 * 1024 * 1024


def sanitize_capture(raw: bytes) -> tuple[bytes, dict[str, int | str]]:
    """Keep only one complete, valid acceptance capture and its vehicle records."""
    source = raw.decode("utf-8", errors="replace")
    output_lines: list[str] = []
    event_lines: list[str] = []
    vehicle_lines: list[str] = []
    capture_started = False
    capture_ended = False

    for line_number, line in enumerate(source.splitlines(), start=1):
        event_count = line.count(EVENT_PREFIX)
        vehicle_count = line.count(VEHICLE_PREFIX)
        if event_count and vehicle_count:
            raise ValueError(f"line {line_number}: multiple staging record types on one line")
        if event_count > 1 or vehicle_count > 1:
            raise ValueError(f"line {line_number}: duplicate staging marker")

        if event_count:
            marker = line.find(EVENT_PREFIX)
            record_line = line[marker:]
            record = _parse_record(record_line[len(EVENT_PREFIX):].strip(), line_number)
            event = record["event"]

            if event == "run_begin":
                if capture_started:
                    raise ValueError(f"line {line_number}: multiple acceptance captures are not allowed")
                capture_started = True
            elif not capture_started:
                raise ValueError(f"line {line_number}: event found outside the acceptance capture")
            elif capture_ended:
                raise ValueError(f"line {line_number}: event found after run_end")

            output_lines.append(record_line)
            event_lines.append(record_line)
            if event == "run_end":
                capture_ended = True
            continue

        if vehicle_count:
            marker = line.find(VEHICLE_PREFIX)
            record_line = line[marker:]
            if not capture_started or capture_ended:
                raise ValueError(f"line {line_number}: vehicle telemetry found outside the acceptance capture")
            output_lines.append(record_line)
            vehicle_lines.append(record_line)

    if not capture_started:
        raise ValueError("no run_begin marker found")
    if not capture_ended:
        raise ValueError("capture is incomplete; run_end marker is missing")

    # Recheck the complete transition contract on the exact exported event lines.
    event_report = parse_staging_log(event_lines)
    if not event_report.passed:
        raise ValueError("staging event contract failed validation: " + "; ".join(event_report.errors))

    # Reuse the strict schema parser so malformed telemetry is never exported.
    parse_vehicle_observations(vehicle_lines)

    payload = ("\n".join(output_lines) + "\n").encode("utf-8")
    if len(payload) > MAX_EXPORT_BYTES:
        raise ValueError(f"sanitized export exceeds the {MAX_EXPORT_BYTES}-byte limit")

    summary: dict[str, int | str] = {
        "event_record_count": len(event_lines),
        "vehicle_sample_count": len(vehicle_lines),
        "output_bytes": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
    }
    return payload, summary


def _read_source(path: Path) -> bytes:
    """Read one bounded regular file without following a symbolic link."""
    try:
        if path.is_symlink():
            raise ValueError("source log must not be a symlink")
        metadata = path.stat()
        if not stat.S_ISREG(metadata.st_mode):
            raise ValueError("source log must be a regular file")
        if metadata.st_size > MAX_SOURCE_BYTES:
            raise ValueError(f"source log exceeds the {MAX_SOURCE_BYTES}-byte limit")
        with path.open("rb") as handle:
            raw = handle.read(MAX_SOURCE_BYTES + 1)
    except OSError as error:
        raise ValueError("source log could not be read") from error

    if len(raw) > MAX_SOURCE_BYTES:
        raise ValueError(f"source log exceeds the {MAX_SOURCE_BYTES}-byte limit")
    return raw


def _write_new_file(path: Path, payload: bytes) -> None:
    """Create a private output file without following links or overwriting data."""
    try:
        if path.is_symlink():
            raise ValueError("output path must not be a symlink")
        if path.exists():
            raise ValueError("output file already exists; choose a new path")
        if not path.parent.is_dir():
            raise ValueError("output directory must already exist")

        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0)
        descriptor = os.open(path, flags, 0o600)
    except FileExistsError as error:
        raise ValueError("output file already exists; choose a new path") from error
    except OSError as error:
        raise ValueError("output file could not be created") from error

    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    except OSError as error:
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass
        raise ValueError("sanitized output could not be written") from error


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Keep only validated staging event and vehicle records from a local console log."
    )
    parser.add_argument("--log", required=True, type=Path, help="local raw server console log")
    parser.add_argument("--output", required=True, type=Path, help="new sanitized output file")
    args = parser.parse_args(argv)

    try:
        if args.log.resolve(strict=False) == args.output.resolve(strict=False):
            raise ValueError("source and output must be different files")
        raw = _read_source(args.log)
        payload, summary = sanitize_capture(raw)
        _write_new_file(args.output, payload)
    except (OSError, UnicodeError, ValueError) as error:
        print(f"Could not sanitize staging log: {error}", file=sys.stderr)
        return 2

    print("Sanitized staging capture created.")
    print(f"Output file: {args.output.name}")
    print(f"Event records: {summary['event_record_count']}")
    print(f"Vehicle telemetry records: {summary['vehicle_sample_count']}")
    print(f"Output size: {summary['output_bytes']} bytes")
    print(f"Output SHA-256: {summary['sha256']}")
    print("Only validated structured records were retained; other console metadata was omitted.")
    print("Bind review records to this sanitized file, not to the original raw console log.")
    print("Scope: format/privacy filtering only; log origin and client runtime are not authenticated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
