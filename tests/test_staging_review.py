#!/usr/bin/env python3
"""Tests for the privacy-safe manual staging review ledger."""

from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools" / "anticheat"))
from staging_review import main, validate_review_record  # noqa: E402

TEMPLATE = ROOT / "docs" / "templates" / "staging-review-template.json"


def valid_record() -> dict:
    """Build a complete structural test record; outcomes remain synthetic."""
    data = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    data["environment"].update({
        "server_commit": "a" * 40,
        "staging_artifact_sha256": "b" * 64,
        "client_build": "test-build-1",
        "started_at": "2026-11-27T10:00:00+07:00",
    })
    return data


class StagingReviewTests(unittest.TestCase):
    def test_template_is_structurally_valid_but_not_executed(self) -> None:
        report = validate_review_record(valid_record())
        self.assertEqual(report["record_status"], "valid")
        self.assertFalse(report["scenario_execution_complete"])
        self.assertEqual(report["evaluation_state"], "incomplete_or_pending")
        self.assertFalse(report["claims"]["false_positive_free_certified"])
        self.assertFalse(report["claims"]["production_ready"])

    def test_fully_recorded_clean_scenarios_are_not_a_product_certificate(self) -> None:
        data = valid_record()
        for observation in data["observations"]:
            observation["result"] = "clean"
            if observation["scenario_id"] == "spectate_roundtrip":
                observation["secondary_client_connected"] = True

        report = validate_review_record(data)
        self.assertEqual(report["record_status"], "valid")
        self.assertTrue(report["scenario_execution_complete"])
        self.assertTrue(report["evidence_review_complete"])
        self.assertEqual(report["evaluation_state"], "observations_reviewed")
        self.assertFalse(report["claims"]["false_positive_free_certified"])

    def test_evidence_requires_category_and_human_decision(self) -> None:
        data = valid_record()
        observation = data["observations"][0]
        observation.update({
            "result": "evidence",
            "evidence_categories": ["movement"],
            "review_decision": "pending",
        })
        report = validate_review_record(data)
        self.assertEqual(report["record_status"], "valid")
        self.assertFalse(report["evidence_review_complete"])
        self.assertEqual(report["review_counts"]["pending"], 1)

    def test_confirmed_false_positive_is_reported_not_suppressed(self) -> None:
        data = valid_record()
        observation = data["observations"][0]
        observation.update({
            "result": "evidence",
            "evidence_categories": ["movement"],
            "review_decision": "confirmed_false_positive",
        })
        report = validate_review_record(data)
        self.assertEqual(report["record_status"], "valid")
        self.assertEqual(report["evaluation_state"], "confirmed_false_positive_present")
        self.assertEqual(report["confirmed_false_positive_count"], 1)

    def test_clean_observation_cannot_hide_evidence(self) -> None:
        data = valid_record()
        data["observations"][0]["evidence_categories"] = ["movement"]
        report = validate_review_record(data)
        self.assertEqual(report["record_status"], "invalid")

    def test_spectate_requires_secondary_client(self) -> None:
        data = valid_record()
        observation = next(item for item in data["observations"] if item["scenario_id"] == "spectate_roundtrip")
        observation["result"] = "clean"
        report = validate_review_record(data)
        self.assertEqual(report["record_status"], "invalid")

    def test_missing_scenario_is_reported(self) -> None:
        data = valid_record()
        data["observations"].pop()
        report = validate_review_record(data)
        self.assertEqual(report["record_status"], "valid")
        self.assertFalse(report["scenario_records_complete"])
        self.assertIn("network_condition_sample", report["missing_scenario_ids"])

    def test_duplicate_scenario_is_rejected(self) -> None:
        data = valid_record()
        data["observations"].append(copy.deepcopy(data["observations"][0]))
        self.assertEqual(validate_review_record(data)["record_status"], "invalid")

    def test_unknown_scenario_is_rejected_without_echoing_value(self) -> None:
        data = valid_record()
        data["observations"][0]["scenario_id"] = "private-player-name"
        report = validate_review_record(data)
        self.assertEqual(report["record_status"], "invalid")
        self.assertNotIn("private-player-name", json.dumps(report))

    def test_blocked_scenario_requires_controlled_reason(self) -> None:
        data = valid_record()
        data["observations"][0].update({"result": "blocked", "block_reason": "second_client_unavailable"})
        report = validate_review_record(data)
        self.assertEqual(report["record_status"], "valid")

        data["observations"][0]["block_reason"] = "free-form sensitive text"
        self.assertEqual(validate_review_record(data)["record_status"], "invalid")

    def test_identity_like_environment_fields_are_rejected(self) -> None:
        data = valid_record()
        data["environment"]["device_imei"] = "123456789012345"
        report = validate_review_record(data)
        self.assertEqual(report["record_status"], "invalid")

    def test_invalid_commit_and_timezone_are_rejected(self) -> None:
        data = valid_record()
        data["environment"]["server_commit"] = "main"
        data["environment"]["started_at"] = "2026-11-27T10:00:00"
        report = validate_review_record(data)
        self.assertEqual(report["record_status"], "invalid")

    def test_cli_emits_machine_readable_summary(self) -> None:
        data = valid_record()
        with tempfile.TemporaryDirectory() as directory:
            record_path = Path(directory) / "review.json"
            record_path.write_text(json.dumps(data), encoding="utf-8")
            from contextlib import redirect_stdout
            from io import StringIO
            output = StringIO()
            with redirect_stdout(output):
                exit_code = main(["--record", str(record_path)])

        self.assertEqual(exit_code, 0)
        self.assertEqual(json.loads(output.getvalue())["record_status"], "valid")


if __name__ == "__main__":
    unittest.main(verbosity=2)
