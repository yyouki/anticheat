#!/usr/bin/env python3
"""Unit tests for deterministic anti-cheat telemetry contract fixtures."""

from __future__ import annotations

import copy
import json
import re
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

    def test_model_reads_numeric_thresholds_from_pawn_includes(self) -> None:
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
        # Test schema validation directly; this must not depend on model initialization.
        with self.assertRaisesRegex(ValueError, "unsupported type"):
            validate_fixture(fixture)

    def test_staging_harness_uses_the_public_persistence_contract(self) -> None:
        staging = (ROOT / "examples" / "staging.pwn").read_text(encoding="utf-8")
        config = json.loads(
            (ROOT / "examples" / "staging" / "config.json").read_text(encoding="utf-8")
        )
        guide = (ROOT / "examples" / "staging" / "README.md").read_text(encoding="utf-8")

        self.assertIn("AC_BeginAccountLoad", staging)
        self.assertIn("AC_ApplyPersistentState", staging)
        self.assertIn("AC_StageSavedLastStrikeAt", staging)
        self.assertIn("score_decay_at, strike_decay_at, last_strike_at", staging)
        self.assertLess(
            staging.index("AC_NotifyLegitimateTeleport(playerid);"),
            staging.index("SetPlayerPos(playerid, x + 8.0"),
        )
        self.assertIn("AC_NotifyLegitimateVehicleChange(playerid);", staging)
        self.assertFalse(config["announce"])
        self.assertFalse(config["enable_query"])
        self.assertFalse(config["rcon"]["enable"])
        self.assertEqual(config["pawn"]["main_scripts"], ["ac-staging 1"])
        self.assertIn("lost when the server process restarts", guide)

    def test_staging_session_selftest_covers_persistence_guards(self) -> None:
        staging = (ROOT / "examples" / "staging.pwn").read_text(encoding="utf-8")
        guide = (ROOT / "examples" / "staging" / "README.md").read_text(encoding="utf-8")

        self.assertIn('"/acstagetest"', staging)
        self.assertIn("stale session token rejected", staging)
        self.assertIn("account ID mismatch rejected", staging)
        self.assertIn("duplicate account load rejected", staging)
        self.assertIn("strike cooldown timestamp remains separate", staging)
        self.assertIn("persistence callback saves score, strikes and cooldown timestamp", staging)
        self.assertIn("saved state restored after simulated session reconnect", staging)
        self.assertIn("original synthetic account restored", staging)
        self.assertIn("real game client remains connected", guide)
        self.assertIn("2000000000", guide)

    def test_legal_transition_helpers_validate_and_share_grace_reset(self) -> None:
        core = (ROOT / "include" / "ac" / "core.inc").read_text(encoding="utf-8")
        integration = (ROOT / "docs" / "INTEGRATION.md").read_text(encoding="utf-8")

        state_change = re.search(
            r"stock AC_NotifyLegitimateStateChange\(.*?\)\s*\{(.*?)\n\}",
            core,
            re.DOTALL,
        )
        self.assertIsNotNone(state_change)
        self.assertIn("AC_IsValidPlayerId(playerid)", state_change.group(1))
        self.assertIn("AC_NotifyLegitimateTeleport(playerid, milliseconds)", state_change.group(1))

        helpers = (
            "AC_NotifyLegitimateInteriorChange",
            "AC_NotifyLegitimateVirtualWorldChange",
            "AC_NotifyLegitimateSpectateChange",
        )
        for helper in helpers:
            with self.subTest(helper=helper):
                body = re.search(
                    rf"stock {helper}\(playerid, milliseconds = AC_DEFAULT_GRACE_MS\)\s*\{{(.*?)\n\}}",
                    core,
                    re.DOTALL,
                )
                self.assertIsNotNone(body)
                self.assertIn("AC_IsValidPlayerId(playerid)", body.group(1))
                self.assertIn("IsPlayerConnected(playerid)", body.group(1))
                self.assertIn("AC_NotifyLegitimateStateChange(playerid, milliseconds)", body.group(1))
                self.assertIn(helper, integration)

        self.assertIn("SetPlayerInterior", integration)
        self.assertIn("SetPlayerVirtualWorld", integration)
        self.assertIn("TogglePlayerSpectating", integration)
        self.assertIn("Only server-controlled legal actions", integration)

    def test_openmp_runtime_smoke_script_checks_boot_and_stops_server(self) -> None:
        script = (ROOT / "tools" / "anticheat" / "openmp_runtime_smoke.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("[AC-STAGE] Staging gamemode initialized.", script)
        self.assertIn("subprocess.Popen", script)
        self.assertIn("stop_server(process)", script)
        self.assertIn("--server-root", script)

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
        self.assertIn("AC_LastStrikeAt[playerid] = last_strike_at", core)
        self.assertIn('"AC_OnPersistenceSave", "ddddddd"', core)


if __name__ == "__main__":
    unittest.main(verbosity=2)
