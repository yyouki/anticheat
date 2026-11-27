#!/usr/bin/env python3
"""Repository-level guardrails for the standalone Pawn anti-cheat core."""

from pathlib import Path
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

def main() -> int:
    sources = {path: read(path) for path in REQUIRED}
    combined = "\n".join(
        value for path, value in sources.items() if path.startswith("include/")
    )

    config = sources["include/ac/config.inc"]
    assert "AC_ENABLE_CLIENT_MEMORY_CHECKS       (0)" in config
    assert "AC_ENABLE_COMBAT_CADENCE             (0)" in config
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

    print(f"Anti-cheat static audit passed ({len(REQUIRED)} required files).")
    return 0

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as error:
        print(f"Anti-cheat static audit failed: {error}", file=sys.stderr)
        raise SystemExit(1)
