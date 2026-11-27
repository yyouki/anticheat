#!/usr/bin/env python3
"""Tests for multi-run staging review aggregation."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools" / "anticheat"
sys.path.insert(0, str(TOOLS))
from staging_review import validate_review_record  # noqa: E402
from staging_review_batch import aggregate_records, main  # noqa: E402

TEMPLATE = ROOT / "docs" / "templates" / "staging-review-template.json"


def valid_record(run_id: str = "run-001") -> dict:
    """Create a structurally valid synthetic record for aggregation tests."""
    data = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    data["run_id"] = run_id
    data["environment"].update({
        "server_commit": "a" * 40,
        "staging_artifact_sha256": "b" * 64,
        "capture_sha256": hashlib.sha256(run_id.encode("utf-8")).hexdigest(),
        "client_build": "test-build-1",
        "started_at": "2026-11-27T10:00:00+07:00",
    })
    return data


def mark_all_clean(record: dict) -> dict:
    for observation in record["observations"]:
        observation["result"] = "clean"
        if observation["scenario_id"] == "spectate_roundtrip":
            observation["secondary_client_connected"] = True
    return record


class StagingReviewBatchTests(unittest.TestCase):
    def test_aggregates_repeated_runs_for_same_environment(self) -> None:
        first = mark_all_clean(valid_record("run-001"))
        second = mark_all_clean(valid_record("run-002"))
        report = aggregate_records([first, second])

        self.assertEqual(report["status"], "valid")
        self.assertEqual(report["group_count"], 1)
        self.assertEqual(report["groups"][0]["run_count"], 2)
        self.assertEqual(report["totals"]["result_counts"]["clean"], 22)
        self.assertEqual(report["groups"][0]["scenario_result_counts"]["walk_idle"]["clean"], 2)
        self.assertFalse(report["claims"]["false_positive_free_certified"])
        self.assertFalse(report["interpretation"]["false_positive_rate_estimated"])

    def test_separates_client_and_network_profiles(self) -> None:
        android = mark_all_clean(valid_record("run-001"))
        windows = mark_all_clean(valid_record("run-002"))
        windows["environment"]["client_platform"] = "windows"
        windows["environment"]["network_profile"] = "high_ping"
        report = aggregate_records([android, windows])

        self.assertEqual(report["group_count"], 2)
        self.assertEqual(
            {item["environment"]["client_platform"] for item in report["groups"]},
            {"android", "windows"},
        )

    def test_keeps_confirmed_false_positive_visible(self) -> None:
        record = valid_record()
        record["observations"][0].update({
            "result": "evidence",
            "evidence_categories": ["movement"],
            "review_decision": "confirmed_false_positive",
        })
        report = aggregate_records([record])
        self.assertEqual(report["totals"]["confirmed_false_positive_count"], 1)
        self.assertEqual(report["totals"]["review_decision_counts"]["confirmed_false_positive"], 1)

    def test_rejects_duplicate_capture_hashes(self) -> None:
        first = valid_record("run-001")
        second = valid_record("run-002")
        second["environment"]["capture_sha256"] = first["environment"]["capture_sha256"]
        report = aggregate_records([first, second])
        self.assertEqual(report["status"], "invalid")
        self.assertIn("duplicate capture_sha256 detected", report["errors"])

    def test_rejects_duplicate_run_ids(self) -> None:
        first = valid_record("run-001")
        second = valid_record("run-001")
        report = aggregate_records([first, second])
        self.assertEqual(report["status"], "invalid")
        self.assertIn("duplicate run_id detected", report["errors"])

    def test_rejects_any_invalid_record_without_partial_success(self) -> None:
        first = valid_record("run-001")
        invalid = valid_record("run-002")
        invalid["environment"]["client_platform"] = "unknown"
        report = aggregate_records([first, invalid])
        self.assertEqual(report["status"], "invalid")
        self.assertEqual(report["valid_record_count"], 1)
        self.assertFalse(report["claims"]["independently_verified"])

    def test_rejects_empty_and_oversized_batches(self) -> None:
        self.assertEqual(aggregate_records([])["status"], "invalid")
        oversized = [valid_record(f"run-{index:03d}") for index in range(501)]
        self.assertEqual(aggregate_records(oversized)["status"], "invalid")

    def test_cli_rejects_oversized_record_file(self) -> None:
        from contextlib import redirect_stdout
        from io import StringIO

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "oversized.json"
            path.write_text(" " * (1_048_577), encoding="utf-8")
            output = StringIO()
            with redirect_stdout(output):
                exit_code = main(["--records-dir", directory])

        self.assertEqual(exit_code, 1)
        self.assertEqual(json.loads(output.getvalue())["status"], "invalid")

    def test_cli_reads_local_records_and_emits_json(self) -> None:
        from contextlib import redirect_stdout
        from io import StringIO

        with tempfile.TemporaryDirectory() as directory:
            record = mark_all_clean(valid_record())
            (Path(directory) / "review.json").write_text(json.dumps(record), encoding="utf-8")
            output = StringIO()
            with redirect_stdout(output):
                exit_code = main(["--records-dir", directory])

        self.assertEqual(exit_code, 0)
        self.assertEqual(json.loads(output.getvalue())["record_count"], 1)

    def test_schema_version_rejects_boolean_in_single_record(self) -> None:
        record = valid_record()
        record["schema_version"] = True
        self.assertEqual(validate_review_record(record)["record_status"], "invalid")


if __name__ == "__main__":
    unittest.main(verbosity=2)
