#!/usr/bin/env python3
"""Tests for binding local review records to exact staging capture bytes."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools" / "anticheat"
sys.path.insert(0, str(TOOLS))
from staging_review_capture import main, validate_capture_binding  # noqa: E402

TEMPLATE = ROOT / "docs" / "templates" / "staging-review-template.json"
CAPTURE = ROOT / "tests" / "fixtures" / "staging_acceptance_success.log"


def valid_record(capture_sha256: str) -> dict:
    """Build a valid schema-v2 synthetic review record."""
    data = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    data["environment"].update({
        "server_commit": "a" * 40,
        "staging_artifact_sha256": "b" * 64,
        "capture_sha256": capture_sha256,
        "client_build": "test-build-1",
        "started_at": "2026-11-27T10:00:00+07:00",
    })
    return data


class StagingReviewCaptureTests(unittest.TestCase):
    def test_matching_digest_and_complete_capture_pass(self) -> None:
        digest = hashlib.sha256(CAPTURE.read_bytes()).hexdigest()
        report, updated = validate_capture_binding(valid_record(digest), CAPTURE)
        self.assertEqual(report["status"], "valid")
        self.assertTrue(report["binding_verified"])
        self.assertIsNone(updated)
        self.assertFalse(report["claims"]["client_runtime_verified"])
        self.assertFalse(report["claims"]["log_origin_authenticated"])

    def test_digest_mismatch_is_rejected(self) -> None:
        report, _ = validate_capture_binding(valid_record("c" * 64), CAPTURE)
        self.assertEqual(report["status"], "invalid")
        self.assertFalse(report["binding_verified"])
        self.assertIn("does not match", report["errors"][0])

    def test_write_mode_generates_digest_and_schema_v2_record(self) -> None:
        source = json.loads(TEMPLATE.read_text(encoding="utf-8"))
        source["schema_version"] = 1
        source["environment"].update({
            "server_commit": "a" * 40,
            "staging_artifact_sha256": "b" * 64,
            "client_build": "test-build-1",
            "started_at": "2026-11-27T10:00:00+07:00",
        })
        report, updated = validate_capture_binding(source, CAPTURE, write_digest=True)
        self.assertEqual(report["status"], "valid")
        self.assertTrue(report["record_updated"])
        self.assertEqual(updated["schema_version"], 2)
        self.assertEqual(
            updated["environment"]["capture_sha256"],
            hashlib.sha256(CAPTURE.read_bytes()).hexdigest(),
        )

    def test_invalid_capture_sequence_is_rejected(self) -> None:
        raw = CAPTURE.read_text(encoding="utf-8").replace("event=run_end", "event=run_abort")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "invalid.log"
            path.write_text(raw, encoding="utf-8")
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            report, _ = validate_capture_binding(valid_record(digest), path)
        self.assertEqual(report["status"], "invalid")
        self.assertEqual(report["capture_contract_status"], "fail")

    def test_symlink_capture_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            link = Path(directory) / "capture.log"
            try:
                link.symlink_to(CAPTURE)
            except (OSError, NotImplementedError):
                self.skipTest("symlinks are unavailable on this platform")
            report, _ = validate_capture_binding(
                valid_record(hashlib.sha256(CAPTURE.read_bytes()).hexdigest()),
                link,
            )
        self.assertEqual(report["status"], "invalid")
        self.assertIn("symlink", report["errors"][0])

    def test_cli_writes_digest_only_after_validation(self) -> None:
        from contextlib import redirect_stdout
        from io import StringIO

        with tempfile.TemporaryDirectory() as directory:
            record_path = Path(directory) / "review.json"
            data = valid_record("")
            data["schema_version"] = 1
            record_path.write_text(json.dumps(data), encoding="utf-8")
            output = StringIO()
            with redirect_stdout(output):
                exit_code = main([
                    "--record", str(record_path),
                    "--capture-log", str(CAPTURE),
                    "--write-digest",
                ])
            self.assertEqual(exit_code, 0)
            saved = json.loads(record_path.read_text(encoding="utf-8"))
            self.assertEqual(saved["schema_version"], 2)
            self.assertEqual(
                saved["environment"]["capture_sha256"],
                hashlib.sha256(CAPTURE.read_bytes()).hexdigest(),
            )
            payload = json.loads(output.getvalue())
            self.assertTrue(payload["record_updated"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
