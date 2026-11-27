#!/usr/bin/env python3
"""Bind a local staging review record to one exact, structurally valid capture file."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import stat
import tempfile
from typing import Any

from staging_report import parse_staging_log
from staging_review import validate_review_record

MAX_CAPTURE_BYTES = 32 * 1024 * 1024
MAX_RECORD_BYTES = 1_048_576
SCHEMA_VERSION = 2


def _read_capture(path: Path) -> tuple[str | None, Any | None, list[str]]:
    """Read one bounded non-symlink file, hash and parse the same exact bytes."""
    try:
        if path.is_symlink():
            return None, None, ["capture log must not be a symlink"]
        metadata = path.stat()
        if not stat.S_ISREG(metadata.st_mode):
            return None, None, ["capture log must be a regular file"]
        if metadata.st_size > MAX_CAPTURE_BYTES:
            return None, None, [f"capture log exceeds the {MAX_CAPTURE_BYTES}-byte limit"]
        with path.open("rb") as handle:
            raw = handle.read(MAX_CAPTURE_BYTES + 1)
    except OSError:
        return None, None, ["capture log could not be read"]

    if len(raw) > MAX_CAPTURE_BYTES:
        return None, None, [f"capture log exceeds the {MAX_CAPTURE_BYTES}-byte limit"]

    digest = hashlib.sha256(raw).hexdigest()
    report = parse_staging_log(raw.decode("utf-8", errors="replace").splitlines())
    return digest, report, []


def validate_capture_binding(
    data: Any,
    capture_log: Path,
    *,
    write_digest: bool = False,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    """Validate a review record and prove its declared digest matches a passing capture."""
    working = copy.deepcopy(data) if isinstance(data, dict) else data
    if write_digest and isinstance(working, dict):
        environment = working.get("environment")
        if isinstance(environment, dict):
            # Explicit write mode also migrates the record to the schema-v2 contract.
            working["schema_version"] = SCHEMA_VERSION
            environment["capture_sha256"] = "0" * 64

    record_report = validate_review_record(working)
    if record_report["record_status"] != "valid":
        return {
            "status": "invalid",
            "errors": ["review record failed schema and observation validation"],
            "claims": {
                "client_runtime_verified": False,
                "log_origin_authenticated": False,
                "production_ready": False,
            },
        }, None

    digest, capture_report, read_errors = _read_capture(capture_log)
    if read_errors:
        return {
            "status": "invalid",
            "errors": read_errors,
            "claims": {
                "client_runtime_verified": False,
                "log_origin_authenticated": False,
                "production_ready": False,
            },
        }, None

    if capture_report is None or not capture_report.passed:
        return {
            "status": "invalid",
            "capture_sha256": digest,
            "capture_contract_status": "fail",
            "errors": list(capture_report.errors) if capture_report is not None else ["capture report unavailable"],
            "claims": {
                "client_runtime_verified": False,
                "log_origin_authenticated": False,
                "production_ready": False,
            },
        }, None

    declared = working["environment"]["capture_sha256"]
    if write_digest:
        working["environment"]["capture_sha256"] = digest
    elif declared != digest:
        return {
            "status": "invalid",
            "capture_sha256": digest,
            "capture_contract_status": "pass",
            "binding_verified": False,
            "errors": ["environment.capture_sha256 does not match the supplied capture log"],
            "claims": {
                "client_runtime_verified": False,
                "log_origin_authenticated": False,
                "production_ready": False,
            },
        }, None

    final_report = validate_review_record(working)
    if final_report["record_status"] != "valid":
        return {
            "status": "invalid",
            "capture_sha256": digest,
            "capture_contract_status": "pass",
            "errors": ["review record failed validation after capture binding"],
            "claims": {
                "client_runtime_verified": False,
                "log_origin_authenticated": False,
                "production_ready": False,
            },
        }, None

    return {
        "status": "valid",
        "run_id": final_report["run_id"],
        "capture_sha256": digest,
        "capture_contract_status": "pass",
        "binding_verified": True,
        "record_updated": write_digest,
        "claims": {
            "client_runtime_verified": False,
            "log_origin_authenticated": False,
            "production_ready": False,
        },
        "limitations": [
            "The digest binds this record to the exact supplied file bytes.",
            "The structured event contract is checked, but log origin is not authenticated.",
            "The tool does not prove that a human executed the recorded scenarios.",
        ],
    }, working if write_digest else None


def _load_record(path: Path) -> tuple[Any | None, list[str]]:
    try:
        if path.is_symlink():
            return None, ["review record must not be a symlink"]
        metadata = path.stat()
        if not stat.S_ISREG(metadata.st_mode):
            return None, ["review record must be a regular file"]
        if metadata.st_size > MAX_RECORD_BYTES:
            return None, ["review record exceeds the 1 MiB limit"]
        with path.open("rb") as handle:
            raw = handle.read(MAX_RECORD_BYTES + 1)
    except OSError:
        return None, ["review record could not be read"]
    if len(raw) > MAX_RECORD_BYTES:
        return None, ["review record exceeds the 1 MiB limit"]
    try:
        return json.loads(raw.decode("utf-8")), []
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None, ["review record is not valid UTF-8 JSON"]


def _write_record_atomically(path: Path, data: dict[str, Any]) -> None:
    """Replace the JSON record only after all validation has passed."""
    if path.is_symlink():
        raise OSError("review record must not be a symlink")
    payload = json.dumps(data, indent=2, sort_keys=True) + "\n"
    temporary_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary_path = handle.name
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, path)
    finally:
        if temporary_path and os.path.exists(temporary_path):
            os.unlink(temporary_path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Verify a review record against one local staging capture without uploading either file."
    )
    parser.add_argument("--record", required=True, type=Path, help="local schema-v2 staging review JSON")
    parser.add_argument("--capture-log", required=True, type=Path, help="local raw staging console log")
    parser.add_argument(
        "--write-digest",
        action="store_true",
        help="after validation, write the capture digest and schema-v2 fields into the review JSON",
    )
    args = parser.parse_args(argv)

    data, load_errors = _load_record(args.record)
    if load_errors:
        print(json.dumps({"status": "invalid", "errors": load_errors}, indent=2, sort_keys=True))
        return 1

    report, updated_record = validate_capture_binding(
        data,
        args.capture_log,
        write_digest=args.write_digest,
    )
    if report["status"] == "valid" and updated_record is not None:
        try:
            _write_record_atomically(args.record, updated_record)
        except OSError:
            report = {
                "status": "invalid",
                "errors": ["validated capture digest could not be written to the review record"],
                "claims": {
                    "client_runtime_verified": False,
                    "log_origin_authenticated": False,
                    "production_ready": False,
                },
            }

    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "valid" else 1


if __name__ == "__main__":
    raise SystemExit(main())
