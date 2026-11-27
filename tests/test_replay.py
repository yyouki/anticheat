#!/usr/bin/env python3
"""Unit tests for deterministic anti-cheat telemetry contract fixtures."""

from __future__ import annotations
import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools" / "anticheat"))
from replay import ReplayEngine, load_constants, replay_file, validate_fixture  # noqa: E402

FIXTURE_DIR = ROOT / "tests" / "fixtures"


class TelemetryReplayTests(unittest.TestCase):
    def test_all_fixtures_match_expected_results(self) -> None:
        fixture_paths = sorted(FIXTURE_DIR.glob("*.json"))
        self.assertGreaterEqual(len(fixture_paths), 8)
        for path in fixture_paths:
            with self.subTest(fixture=path.name):
                replay_file(path)

    def test_model_reads_numeric_thresholds_from_pawn_config(self) -> None:
        constants = load_constants()
        self.assertEqual(constants["AC_SAMPLE_INTERVAL_MS"], 500)
        self.assertEqual(constants["AC_MAX_SAMPLE_GAP_MS"], 1750)
        self.assertEqual(constants["AC_MOVEMENT_REQUIRED_SAMPLES"], 3)
        self.assertEqual(constants["AC_NETWORK_QUALITY_TTL_MS"], 3000)

    def test_out_of_order_timestamps_are_rejected(self) -> None:
        path = FIXTURE_DIR / "sustained_onfoot_speed_anomaly.json"
        fixture = json.loads(path.read_text(encoding="utf-8"))
        invalid = copy.deepcopy(fixture)
        invalid["events"][2]["at_ms"] = 1200
        with self.assertRaisesRegex(ValueError, "timestamp order"):
            validate_fixture(invalid)

    def test_unknown_event_type_is_rejected(self) -> None:
        fixture = {
            "schema_version": 1,
            "scenario_id": "invalid-event",
            "description": "invalid fixture",
            "events": [{"type": "teleport-anywhere", "at_ms": 1000}],
            "expected": {},
        }
        with self.assertRaisesRegex(ValueError, "unsupported type"):
            ReplayEngine().run(fixture)

    def test_reference_model_contract_matches_pawn_source_gates(self) -> None:
        movement = (ROOT / "include/ac/movement.inc").read_text(encoding="utf-8")
        network = (ROOT / "include/ac/network.inc").read_text(encoding="utf-8")
        evidence = (ROOT / "include/ac/evidence.inc").read_text(encoding="utf-8")
        core = (ROOT / "include/ac/core.inc").read_text(encoding="utf-8")

        self.assertIn("tick - AC_LastUpdateTick[playerid]", movement)
        self.assertIn("elapsed > AC_MAX_SAMPLE_GAP_MS", movement)
        self.assertIn("AC_MovementOverLimitSamples[playerid] >= AC_MOVEMENT_REQUIRED_SAMPLES", movement)
        self.assertIn("ping == 65535", network)
        self.assertIn("AC_NetworkPacketLoss[playerid] >= 15.0", network)
        self.assertIn("AC_NETWORK_QUALITY_TTL_MS", network)
        self.assertIn("other_mask != 0", evidence)
        self.assertIn("AC_SCORE_STRIKE_THRESHOLD", evidence)
        self.assertIn("|| AC_PlayerLoaded[playerid])", core)
        self.assertIn("AC_LastStrikeAt[playerid] = strike_decay_at", core)


if __name__ == "__main__":
    unittest.main(verbosity=2)
