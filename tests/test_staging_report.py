#!/usr/bin/env python3
"""Tests for privacy-safe interactive staging acceptance reports."""

from __future__ import annotations

from contextlib import redirect_stdout
import json
from io import StringIO
from pathlib import Path
import sys
from unittest.mock import patch
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools" / "anticheat"))
from staging_report import main, parse_staging_log, report_to_payload  # noqa: E402

FIXTURES = ROOT / "tests" / "fixtures"


class StagingReportTests(unittest.TestCase):
    def test_synthetic_complete_capture_passes(self) -> None:
        path = FIXTURES / "staging_acceptance_success.log"
        with path.open("r", encoding="utf-8") as handle:
            report = parse_staging_log(handle)
        self.assertTrue(report.passed, report.errors)
        self.assertEqual(report.evidence_count, 0)
        self.assertEqual(report.review_marker_count, 0)

    def test_evidence_during_capture_fails(self) -> None:
        lines = (FIXTURES / "staging_acceptance_success.log").read_text(encoding="utf-8").splitlines()
        lines.insert(-1, "[AC-STAGE-EVENT] schema=1 event=evidence actor=primary category=movement points=2 ping=80")
        report = parse_staging_log(lines)
        self.assertFalse(report.passed)
        self.assertEqual(report.evidence_count, 1)
        self.assertTrue(any("evidence event" in error for error in report.errors))

    def test_review_marker_during_capture_fails(self) -> None:
        lines = (FIXTURES / "staging_acceptance_success.log").read_text(encoding="utf-8").splitlines()
        lines.insert(-1, "[AC-STAGE-EVENT] schema=1 event=review_marker actor=primary strikes=1")
        report = parse_staging_log(lines)
        self.assertFalse(report.passed)
        self.assertEqual(report.review_marker_count, 1)

    def test_missing_interior_callback_fails(self) -> None:
        lines = [
            line for line in (FIXTURES / "staging_acceptance_success.log").read_text(encoding="utf-8").splitlines()
            if "event=interior_callback" not in line
        ]
        report = parse_staging_log(lines)
        self.assertFalse(report.passed)
        self.assertTrue(any("interior_callback" in error for error in report.errors))

    def test_incomplete_capture_fails(self) -> None:
        lines = [
            line for line in (FIXTURES / "staging_acceptance_success.log").read_text(encoding="utf-8").splitlines()
            if "event=run_end" not in line
        ]
        report = parse_staging_log(lines)
        self.assertFalse(report.passed)
        self.assertTrue(any("incomplete" in error for error in report.errors))

    def test_raw_player_identifiers_are_rejected(self) -> None:
        lines = (FIXTURES / "staging_acceptance_success.log").read_text(encoding="utf-8").splitlines()
        lines.insert(1, "[AC-STAGE-EVENT] schema=1 event=evidence actor=primary playerid=7")
        report = parse_staging_log(lines)
        self.assertFalse(report.passed)
        self.assertTrue(any("unsupported field playerid" in error for error in report.errors))

    def test_transition_order_is_enforced(self) -> None:
        lines = (FIXTURES / "staging_acceptance_success.log").read_text(encoding="utf-8").splitlines()
        enter = next(index for index, line in enumerate(lines) if "event=world_enter" in line)
        leave = next(index for index, line in enumerate(lines) if "event=world_exit" in line)
        lines[enter], lines[leave] = lines[leave], lines[enter]
        report = parse_staging_log(lines)
        self.assertFalse(report.passed)
        self.assertTrue(any("world_enter must occur before world_exit" in error for error in report.errors))

    def test_duplicate_fields_are_rejected(self) -> None:
        lines = (FIXTURES / "staging_acceptance_success.log").read_text(encoding="utf-8").splitlines()
        lines.insert(1, "[AC-STAGE-EVENT] schema=1 event=evidence actor=primary category=movement category=vehicle points=1 ping=50")
        report = parse_staging_log(lines)
        self.assertFalse(report.passed)
        self.assertTrue(any("duplicate field category" in error for error in report.errors))

    def test_negative_counters_are_rejected(self) -> None:
        lines = (FIXTURES / "staging_acceptance_success.log").read_text(encoding="utf-8").splitlines()
        lines.insert(1, "[AC-STAGE-EVENT] schema=1 event=evidence actor=primary category=movement points=-1 ping=50")
        report = parse_staging_log(lines)
        self.assertFalse(report.passed)
        self.assertTrue(any("points must not be negative" in error for error in report.errors))

    def test_unknown_spectate_target_role_is_rejected(self) -> None:
        lines = (FIXTURES / "staging_acceptance_success.log").read_text(encoding="utf-8").splitlines()
        index = next(i for i, line in enumerate(lines) if "event=spectate_start" in line)
        lines[index] = lines[index].replace("target=secondary", "target=playerid7")
        report = parse_staging_log(lines)
        self.assertFalse(report.passed)
        self.assertTrue(any("target must use the secondary test role" in error for error in report.errors))

    def test_reason_is_rejected_on_non_abort_event(self) -> None:
        lines = (FIXTURES / "staging_acceptance_success.log").read_text(encoding="utf-8").splitlines()
        lines.insert(1, "[AC-STAGE-EVENT] schema=1 event=teleport actor=primary reason=owner_disconnect")
        report = parse_staging_log(lines)
        self.assertFalse(report.passed)
        self.assertTrue(any("reason is only valid for run_abort" in error for error in report.errors))

    def test_required_transition_fields_are_enforced(self) -> None:
        lines = (FIXTURES / "staging_acceptance_success.log").read_text(encoding="utf-8").splitlines()
        index = next(i for i, line in enumerate(lines) if "event=world_enter" in line)
        lines[index] = "[AC-STAGE-EVENT] schema=1 event=world_enter actor=primary from=0"
        report = parse_staging_log(lines)
        self.assertFalse(report.passed)
        self.assertTrue(any("world_enter missing required field" in error for error in report.errors))

    def test_json_payload_separates_log_pass_from_runtime_validation(self) -> None:
        path = FIXTURES / "staging_acceptance_success.log"
        with path.open("r", encoding="utf-8") as handle:
            payload = report_to_payload(parse_staging_log(handle))

        self.assertEqual(payload["report_schema_version"], 1)
        self.assertEqual(payload["report_type"], "openmp_staging_acceptance")
        self.assertEqual(payload["status"], "pass")
        self.assertTrue(payload["passed"])
        self.assertEqual(payload["validation_scope"], "structured_log_contract")
        self.assertEqual(
            payload["runtime_validation"],
            {
                "client_runtime_verified": False,
                "log_origin_authenticated": False,
                "production_ready": False,
            },
        )
        serialized = json.dumps(payload, sort_keys=True)
        self.assertNotIn("playerid", serialized.lower())
        self.assertNotIn("accountid", serialized.lower())

    def test_json_payload_marks_incomplete_capture_as_failure(self) -> None:
        lines = [
            line for line in (FIXTURES / "staging_acceptance_success.log").read_text(encoding="utf-8").splitlines()
            if "event=run_end" not in line
        ]
        payload = report_to_payload(parse_staging_log(lines))
        self.assertEqual(payload["status"], "fail")
        self.assertFalse(payload["passed"])
        self.assertFalse(payload["runtime_validation"]["production_ready"])

    def test_unknown_event_value_is_not_echoed_into_report(self) -> None:
        lines = (FIXTURES / "staging_acceptance_success.log").read_text(encoding="utf-8").splitlines()
        lines[1] = lines[1].replace("event=teleport", "event=private-account-value")
        report = parse_staging_log(lines)
        self.assertFalse(report.passed)
        self.assertTrue(any("unsupported event value" in error for error in report.errors))
        self.assertNotIn("private-account-value", json.dumps(report_to_payload(report)))

    def test_json_cli_outputs_only_the_report_payload(self) -> None:
        output = StringIO()
        fixture = FIXTURES / "staging_acceptance_success.log"
        with patch("sys.argv", ["staging_report.py", "--log", str(fixture), "--json"]):
            with redirect_stdout(output):
                exit_code = main()

        self.assertEqual(exit_code, 0)
        payload = json.loads(output.getvalue())
        self.assertEqual(payload["status"], "pass")
        self.assertFalse(payload["runtime_validation"]["client_runtime_verified"])

    def test_source_registers_capture_commands_and_keeps_records_pseudonymous(self) -> None:
        staging = (ROOT / "examples" / "staging.pwn").read_text(encoding="utf-8")
        self.assertIn('"/acstagelogbegin"', staging)
        self.assertIn('"/acstagelogend"', staging)
        self.assertIn('[AC-STAGE-EVENT] schema=1 event=%s actor=primary%s', staging)
        self.assertIn('AC_StageLogEvent(playerid, "evidence", details)', staging)
        self.assertIn('AC_StageLogEvent(playerid, "review_marker", details)', staging)
        self.assertNotIn('LOAD account=%d session=%d', staging)
        self.assertNotIn('SAVE account=%d', staging)


if __name__ == "__main__":
    unittest.main(verbosity=2)
