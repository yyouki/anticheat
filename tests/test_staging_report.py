#!/usr/bin/env python3
"""Tests for privacy-safe interactive staging acceptance reports."""

from __future__ import annotations

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools" / "anticheat"))
from staging_report import parse_staging_log  # noqa: E402

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
