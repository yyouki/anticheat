#!/usr/bin/env python3
"""Repository-level guardrails for the standalone Pawn anti-cheat core."""

from pathlib import Path
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[2]

REQUIRED = [
    "include/ac.inc",
    "include/ac/config.inc",
    "include/ac/state.inc",
    "include/ac/network.inc",
    "include/ac/core.inc",
    "include/ac/evidence.inc",
    "include/ac/player_state.inc",
    "include/ac/movement.inc",
    "include/ac/vehicle.inc",
    "include/ac/combat.inc",
    "include/ac/integrity.inc",
    "include/ac/admin.inc",
    "examples/smoke.pwn",
    "examples/feature_gate_smoke.pwn",
    "examples/staging.pwn",
    "examples/staging/config.json",
    "examples/staging/README.md",
    "tools/anticheat/replay.py",
    "tools/anticheat/openmp_runtime_smoke.py",
    "tests/test_replay.py",
    "tests/fixtures/legal_movement_during_and_after_grace.json",
    "tests/fixtures/sustained_onfoot_speed_anomaly.json",
    "tests/fixtures/network_quality_resets_movement_streak.json",
    "tests/fixtures/sample_gap_and_world_transition_reset.json",
    "tests/fixtures/single_category_threshold_does_not_strike.json",
    "tests/fixtures/cross_category_evidence_can_create_review_strike.json",
    "tests/fixtures/expired_packet_loss_measurement_does_not_suppress.json",
    "tests/fixtures/stale_and_duplicate_account_loads_are_rejected.json",
    "tests/fixtures/strike_cooldown_survives_reconnect.json",
    "tests/fixtures/expired_strike_cooldown_not_restarted_by_decay_timestamp.json",
    "docs/TELEMETRY_REPLAY.md",
    "docs/ARCHITECTURE.md",
    "docs/INTEGRATION.md",
    "docs/VALIDATION.md",
    "experiments/README.md",
]

def read(relative: str) -> str:
    path = ROOT / relative
    if not path.is_file():
        raise AssertionError(f"required file missing: {relative}")
    return path.read_text(encoding="utf-8")


def function_body(source: str, name: str) -> str:
    """Return one Pawn stock function body using brace-depth matching."""
    pattern = r"\bstock\s+(?:bool:)?"+re.escape(name)+r"\s*\([^;]*?\)\s*\{"
    match = re.search(pattern, source, re.DOTALL)
    if not match:
        raise AssertionError(f"required function missing: {name}")

    opening = match.end() - 1
    depth = 0
    for index in range(opening, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[opening + 1:index]
    raise AssertionError(f"unterminated function body: {name}")


def require_player_id_guards(relative: str, names: tuple[str, ...], sources: dict[str, str]) -> None:
    for name in names:
        body = function_body(sources[relative], name)
        assert "AC_IsValidPlayerId(playerid)" in body, (
            f"{relative}:{name} must validate playerid before array access"
        )

def main() -> int:
    sources = {path: read(path) for path in REQUIRED}
    combined = "\n".join(
        value for path, value in sources.items() if path.startswith("include/")
    )

    config = sources["include/ac/config.inc"]
    assert "#if !defined AC_ENABLE_CLIENT_MEMORY_CHECKS" in config
    assert "#if !defined AC_ENABLE_COMBAT_CADENCE" in config
    assert "AC_ENABLE_CLIENT_MEMORY_CHECKS   (0)" in config
    assert "AC_ENABLE_COMBAT_CADENCE         (0)" in config
    assert "#define AC_ENABLE_COMBAT_CADENCE (1)" in sources["examples/feature_gate_smoke.pwn"]
    assert "feature-gate-smoke.amx" in read(".github/workflows/ci.yml")
    assert "AC_SAMPLE_INTERVAL_MS                (500)" in config

    umbrella = sources["include/ac.inc"]
    for module in ("config", "state", "network", "core", "evidence", "player_state",
                   "movement", "vehicle", "combat", "integrity", "admin"):
        assert f"ac/{module}" in umbrella, f"umbrella missing {module}"

    assert "AC_EVIDENCE_WINDOW_SECONDS" in sources["include/ac/evidence.inc"]
    assert "other_mask != 0" in sources["include/ac/evidence.inc"]
    assert "AC_OnPersistenceSave" in sources["include/ac/core.inc"]
    assert "AC_SessionToken" in sources["include/ac/core.inc"]
    assert "AC_NETWORK_QUALITY_TTL_MS" in sources["include/ac/network.inc"]
    assert "AC_MOVEMENT_REQUIRED_SAMPLES" in sources["include/ac/movement.inc"]
    assert "AC_VEHICLE_REQUIRED_SAMPLES" in sources["include/ac/vehicle.inc"]

    # Player-indexed helpers must reject out-of-range IDs before array access.
    require_player_id_guards("include/ac/state.inc", (
        "AC_ResetSampling", "AC_ResetEvidence", "AC_ResetPlayer"
    ), sources)
    require_player_id_guards("include/ac/core.inc", (
        "AC_AdvanceSessionToken", "AC_GetSessionToken", "AC_OnPlayerConnect",
        "AC_OnPlayerDisconnect", "AC_SetIdentity", "AC_BeginAccountLoad",
        "AC_ApplyPersistentState", "AC_SetEnabled", "AC_IsMonitored",
        "AC_NotifyLegitimateTeleport", "AC_NotifyLegitimateStateChange",
        "AC_NotifyLegitimateInteriorChange", "AC_NotifyLegitimateVirtualWorldChange",
        "AC_NotifyLegitimateSpectateChange", "AC_NotifyLegitimateVehicleChange",
        "AC_NotifyLegitimateHealthChange", "AC_IsInGrace",
        "AC_SavePersistentState", "AC_ApplyDecay"
    ), sources)
    require_player_id_guards("include/ac/network.inc", (
        "AC_SetNetworkQuality", "AC_GetPing"
    ), sources)
    require_player_id_guards("include/ac/evidence.inc", (
        "AC_GetSuspicionScore", "AC_GetStrikeCount", "AC_GetEvidenceCount",
        "AC_GetEvidence", "AC_ClearPlayerEvidence", "AC_ClearPlayerReviewState"
    ), sources)
    require_player_id_guards("include/ac/player_state.inc", ("AC_OnPlayerDeath",), sources)
    require_player_id_guards("include/ac/integrity.inc", ("AC_GetClientIntegrityStatus",), sources)
    for admin_function in ("AC_AdminStatus", "AC_AdminEvidence", "AC_AdminClear"):
        admin_body = function_body(sources["include/ac/admin.inc"], admin_function)
        assert "AC_IsValidPlayerId(adminid)" in admin_body
        assert "AC_IsValidPlayerId(targetid)" in admin_body
    require_player_id_guards("include/ac/vehicle.inc", ("AC_OnVehicleSample",), sources)
    require_player_id_guards("include/ac/movement.inc", ("AC_UpdateMovementBaseline",), sources)
    assert "|| AC_PlayerLoaded[playerid])" in function_body(
        sources["include/ac/core.inc"], "AC_ApplyPersistentState"
    ), "duplicate account-load completions must be rejected"
    assert "AC_LastStrikeAt[playerid] = last_strike_at" in function_body(
        sources["include/ac/core.inc"], "AC_ApplyPersistentState"
    ), "active strike cooldown must be restored from its own persisted timestamp"
    for transition_helper in (
        "AC_NotifyLegitimateInteriorChange",
        "AC_NotifyLegitimateVirtualWorldChange",
        "AC_NotifyLegitimateSpectateChange",
    ):
        body = function_body(sources["include/ac/core.inc"], transition_helper)
        assert "AC_IsValidPlayerId(playerid)" in body
        assert "IsPlayerConnected(playerid)" in body
        assert "AC_NotifyLegitimateStateChange(playerid, milliseconds)" in body

    assert '"AC_OnPersistenceSave", "ddddddd"' in sources["include/ac/core.inc"]

    # The library must remain framework/database independent.
    forbidden = ("PlayerData[", "AccountData[", "mysql_tquery", "SQL_Connect", "PawnPlus", "pp-hooks")
    for token in forbidden:
        assert token not in combined, f"production include depends on forbidden host symbol: {token}"

    # No automatic punishment or generic client-memory scan belongs in v1.
    assert not re.search(r"\b(?:Kick|Ban|BanEx)\s*\(", combined)
    assert "SendClientCheck(" not in combined
    assert "AC_ENABLE_CLIENT_MEMORY_CHECKS" in sources["include/ac/integrity.inc"]

    # Admin helpers intentionally do not decide permissions.
    assert "MUST" in sources["include/ac/admin.inc"]
    assert "permission" in sources["docs/INTEGRATION.md"].lower()

    assert "schema_version" in sources["docs/TELEMETRY_REPLAY.md"]
    assert "reference model" in sources["tools/anticheat/replay.py"]
    assert "unittest" in sources["tests/test_replay.py"]

    # The staging sample must exercise the public lifecycle/persistence contract
    # without adding a database, production auth provider, or automatic sanctions.
    staging = sources["examples/staging.pwn"]
    staging_readme = sources["examples/staging/README.md"]
    staging_config = json.loads(sources["examples/staging/config.json"])
    assert "AC_BeginAccountLoad" in staging
    assert "AC_ApplyPersistentState" in staging
    assert "AC_StageSavedLastStrikeAt" in staging
    assert (
        "public AC_OnPersistenceSave(playerid, accountid, score, strikes, "
        "score_decay_at, strike_decay_at, last_strike_at)" in staging
    )
    assert "AC_NotifyLegitimateTeleport(playerid);" in staging
    assert staging.index("AC_NotifyLegitimateTeleport(playerid);") < staging.index(
        "SetPlayerPos(playerid, x + 8.0"
    ), "staging gamemode must notify before its legal teleport"
    assert "AC_NotifyLegitimateVehicleChange(playerid);" in staging
    assert '"/acstagetest"' in staging
    for selftest_case in (
        "stale session token rejected",
        "account ID mismatch rejected",
        "duplicate account load rejected",
        "strike cooldown timestamp remains separate",
        "persistence callback saves score, strikes and cooldown timestamp",
        "saved state restored after simulated session reconnect",
        "original synthetic account restored",
        "interior change notification starts grace window",
        "virtual world change notification starts grace window",
        "spectate change notification starts grace window",
    ):
        assert selftest_case in staging, f"staging self-test missing case: {selftest_case}"
    assert "real game client remains connected" in staging_readme
    assert "AC_OnPlayerUpdate(playerid);" in staging
    assert not re.search(r"\b(?:Kick|Ban|BanEx)\s*\(", staging)
    assert staging_config.get("announce") is False
    assert staging_config.get("enable_query") is False
    assert staging_config.get("rcon", {}).get("enable") is False
    assert staging_config.get("pawn", {}).get("main_scripts") == ["ac-staging 1"]
    assert "lost when the server process restarts" in staging_readme
    assert "ac-staging.amx" in read(".github/workflows/ci.yml")
    workflow = read(".github/workflows/ci.yml")
    assert "actions/upload-artifact@v4" in workflow
    assert "openmp-runtime-smoke" in workflow
    assert "actions/download-artifact@v4" in workflow
    assert "v1.6.7.3218" in workflow

    runtime_smoke = sources["tools/anticheat/openmp_runtime_smoke.py"]
    assert "[AC-STAGE] Staging gamemode initialized." in runtime_smoke
    assert "stop_server(process)" in runtime_smoke

    print(f"Anti-cheat static audit passed ({len(REQUIRED)} required files).")
    return 0

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as error:
        print(f"Anti-cheat static audit failed: {error}", file=sys.stderr)
        raise SystemExit(1)
