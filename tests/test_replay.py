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
from replay import (
    ReplayEngine,
    load_constants,
    load_excluded_vehicle_models,
    replay_file,
    validate_fixture,
)  # noqa: E402

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
        self.assertIn("interior change notification starts grace window", staging)
        self.assertIn("virtual world change notification starts grace window", staging)
        self.assertIn("spectate change notification starts grace window", staging)
        self.assertIn("real game client remains connected", guide)
        self.assertIn("2000000000", guide)

    def test_legal_transition_helpers_validate_and_share_grace_reset(self) -> None:
        core = (ROOT / "include" / "ac" / "core.inc").read_text(encoding="utf-8")
        integration = (ROOT / "docs" / "INTEGRATION.md").read_text(encoding="utf-8")

        def pawn_stock_body(name: str) -> str:
            # Match nested Pawn blocks by brace depth instead of a fragile regex.
            start = core.index(f"stock {name}(")
            opening = core.index("{", start)
            depth = 0
            for index in range(opening, len(core)):
                if core[index] == "{":
                    depth += 1
                elif core[index] == "}":
                    depth -= 1
                    if depth == 0:
                        return core[opening + 1:index]
            self.fail(f"unterminated Pawn stock function: {name}")

        state_change = pawn_stock_body("AC_NotifyLegitimateStateChange")
        self.assertIn("AC_IsValidPlayerId(playerid)", state_change)
        self.assertIn("IsPlayerConnected(playerid)", state_change)
        self.assertIn("AC_NotifyLegitimateTeleport(playerid, milliseconds)", state_change)

        helpers = (
            "AC_NotifyLegitimateInteriorChange",
            "AC_NotifyLegitimateVirtualWorldChange",
            "AC_NotifyLegitimateSpectateChange",
        )
        for helper in helpers:
            with self.subTest(helper=helper):
                body = pawn_stock_body(helper)
                self.assertIn("AC_IsValidPlayerId(playerid)", body)
                self.assertIn("IsPlayerConnected(playerid)", body)
                self.assertIn("AC_NotifyLegitimateStateChange(playerid, milliseconds)", body)
                self.assertIn(helper, integration)

        self.assertIn("SetPlayerInterior", integration)
        self.assertIn("SetPlayerVirtualWorld", integration)
        self.assertIn("TogglePlayerSpectating", integration)
        self.assertIn("Only server-controlled legal actions", integration)

    def test_staging_live_transition_commands_notify_before_server_actions(self) -> None:
        staging = (ROOT / "examples" / "staging.pwn").read_text(encoding="utf-8")
        guide = (ROOT / "examples" / "staging" / "README.md").read_text(encoding="utf-8")

        def pawn_stock_body(name: str) -> str:
            # Match nested Pawn blocks by brace depth instead of a fragile regex.
            start = staging.index(f"stock {name}(")
            opening = staging.index("{", start)
            depth = 0
            for index in range(opening, len(staging)):
                if staging[index] == "{":
                    depth += 1
                elif staging[index] == "}":
                    depth -= 1
                    if depth == 0:
                        return staging[opening + 1:index]
            self.fail(f"unterminated Pawn stock function: {name}")

        for command in (
            '"/acstageinterior"',
            '"/acstageworld"',
            '"/acstagespectate "',
            '"/acstageunspectate"',
        ):
            with self.subTest(command=command):
                self.assertIn(command, staging)

        player_id_parser = pawn_stock_body("AC_StageParsePlayerId")
        self.assertIn("return -1;", player_id_parser)
        self.assertIn("new targetid = AC_StageParsePlayerId(cmdtext[17]);", staging)
        self.assertIn("if (targetid < 0 || !AC_IsValidPlayerId(targetid))", staging)

        interior = pawn_stock_body("AC_StageToggleInterior")
        self.assertLess(
            interior.index("AC_NotifyLegitimateInteriorChange(playerid);"),
            interior.index("SetPlayerInterior(playerid, AC_STAGE_TEST_INTERIOR_ID)"),
        )
        self.assertLess(
            interior.index("AC_NotifyLegitimateTeleport(playerid);"),
            interior.index("SetPlayerPos(playerid, -25.7220"),
        )
        self.assertIn("AC_STAGE_TEST_INTERIOR_ID (17)", staging)

        world = pawn_stock_body("AC_StageToggleVirtualWorld")
        self.assertLess(
            world.index("AC_NotifyLegitimateVirtualWorldChange(playerid);"),
            world.index("SetPlayerVirtualWorld(playerid, AC_STAGE_TEST_WORLD_ID)"),
        )
        self.assertIn("AC_STAGE_TEST_WORLD_ID (9000)", staging)

        spectate = pawn_stock_body("AC_StageStartSpectating")
        self.assertLess(
            spectate.index("AC_NotifyLegitimateSpectateChange(playerid);"),
            spectate.index("TogglePlayerSpectating(playerid, true)"),
        )
        self.assertLess(
            spectate.index("TogglePlayerSpectating(playerid, true)"),
            spectate.index("PlayerSpectatePlayer(playerid, targetid)"),
        )

        unspectate = pawn_stock_body("AC_StageEndSpectating")
        self.assertLess(
            unspectate.index("AC_NotifyLegitimateSpectateChange(playerid);"),
            unspectate.index("TogglePlayerSpectating(playerid, false)"),
        )

        restore = pawn_stock_body("AC_StageRestoreSpectateContext")
        for notification, action in (
            ("AC_NotifyLegitimateInteriorChange(playerid);", "SetPlayerInterior("),
            ("AC_NotifyLegitimateVirtualWorldChange(playerid);", "SetPlayerVirtualWorld("),
            ("AC_NotifyLegitimateTeleport(playerid);", "SetPlayerPos("),
        ):
            self.assertLess(restore.index(notification), restore.index(action))

        self.assertIn("OnPlayerInteriorChange", staging)
        self.assertIn("GetPlayerInterior(playerid)", pawn_stock_body("AC_StageShowInfo"))
        self.assertIn("GetPlayerVirtualWorld(playerid)", pawn_stock_body("AC_StageShowInfo"))
        self.assertIn("Connect a second test client", guide)
        self.assertIn("restores the spectator's previous position/context", guide)

    def test_openmp_runtime_smoke_script_checks_boot_and_stops_server(self) -> None:
        script = (ROOT / "tools" / "anticheat" / "openmp_runtime_smoke.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("[AC-STAGE] Staging gamemode initialized.", script)
        self.assertIn("subprocess.Popen", script)
        self.assertIn("stop_server(process)", script)
        self.assertIn("--server-root", script)

    def test_reference_model_reads_vehicle_constants_and_exclusions_from_pawn(self) -> None:
        constants = load_constants()
        vehicle_source = (ROOT / "include" / "ac" / "vehicle.inc").read_text(encoding="utf-8")

        self.assertEqual(constants["AC_VEHICLE_MAX_PING"], 400)
        self.assertEqual(constants["AC_VEHICLE_REQUIRED_SAMPLES"], 3)
        self.assertEqual(constants["AC_VEHICLE_SPEED_FACTOR"], 250.66667)
        self.assertEqual(load_excluded_vehicle_models(), {
            417, 425, 430, 446, 447, 452, 453, 454, 460, 464, 469, 472, 473,
            476, 484, 487, 488, 493, 497, 500, 501, 502, 503, 511, 512, 513,
            519, 520, 537, 538, 548, 553, 563, 577, 592, 593, 595,
        })
        self.assertIn("AC_IsExcludedVehicleModel", vehicle_source)

    def test_vehicle_fixture_contract_rejects_invalid_speed_and_model(self) -> None:
        fixture = {
            "schema_version": 1,
            "scenario_id": "invalid_vehicle_sample",
            "description": "synthetic invalid vehicle event",
            "events": [{
                "type": "vehicle_sample",
                "at_ms": 500,
                "vehicle_id": 1,
                "vehicle_model": 411,
                "speed_kmh": 400.0,
                "ping": 50,
            }],
            "expected": {},
        }
        invalid = copy.deepcopy(fixture)
        invalid["events"][0]["speed_kmh"] = float("nan")
        with self.assertRaisesRegex(ValueError, "finite non-negative"):
            validate_fixture(invalid)

        invalid = copy.deepcopy(fixture)
        invalid["events"][0]["vehicle_model"] = 999
        with self.assertRaisesRegex(ValueError, "GTA SA vehicle model"):
            validate_fixture(invalid)

    def test_reference_model_contract_matches_pawn_source_gates(self) -> None:
        movement = (ROOT / "include/ac/movement.inc").read_text(encoding="utf-8")
        vehicle = (ROOT / "include/ac/vehicle.inc").read_text(encoding="utf-8")
        network = (ROOT / "include/ac/network.inc").read_text(encoding="utf-8")
        evidence = (ROOT / "include/ac/evidence.inc").read_text(encoding="utf-8")
        core = (ROOT / "include/ac/core.inc").read_text(encoding="utf-8")

        self.assertIn("tick - AC_LastUpdateTick[playerid]", movement)
        self.assertIn("elapsed > AC_MAX_SAMPLE_GAP_MS", movement)
        self.assertIn("AC_MovementOverLimitSamples[playerid] >= AC_MOVEMENT_REQUIRED_SAMPLES", movement)
        self.assertIn("ping == 65535", network)
        self.assertIn("AC_NetworkPacketLoss[playerid] >= 15.0", network)
        self.assertIn("AC_NETWORK_QUALITY_TTL_MS", network)
        self.assertIn("AC_VEHICLE_REQUIRED_SAMPLES", vehicle)
        self.assertIn("AC_VEHICLE_MAX_SPEED_KMH", vehicle)
        self.assertIn("AC_IsExcludedVehicleModel", vehicle)
        self.assertIn("AC_IsNetworkSampleReliable(playerid, AC_VEHICLE_MAX_PING)", vehicle)
        self.assertIn("other_mask != 0", evidence)
        self.assertIn("AC_SCORE_STRIKE_THRESHOLD", evidence)
        self.assertIn("|| AC_PlayerLoaded[playerid])", core)
        self.assertIn("AC_LastStrikeAt[playerid] = last_strike_at", core)
        self.assertIn('"AC_OnPersistenceSave", "ddddddd"', core)


if __name__ == "__main__":
    unittest.main(verbosity=2)
