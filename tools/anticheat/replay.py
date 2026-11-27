#!/usr/bin/env python3
"""Deterministic reference model and replay tool for anti-cheat telemetry fixtures.

This model validates the documented detector contract. It is not an open.mp
runtime and does not execute Pawn bytecode; production behavior still requires
staging-server validation.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
CATEGORY_IDS = {
    "movement": 0,
    "vehicle": 1,
    "combat": 2,
    "state": 3,
    "integrity": 4,
}
CATEGORY_NAMES = {value: key for key, value in CATEGORY_IDS.items()}

CONSTANT_NAMES = (
    "AC_EVIDENCE_WINDOW_SECONDS",
    "AC_CATEGORY_COOLDOWN_SECONDS",
    "AC_SCORE_STRIKE_THRESHOLD",
    "AC_SCORE_STRIKE_REDUCTION",
    "AC_STRIKE_COOLDOWN_SECONDS",
    "AC_SAMPLE_INTERVAL_MS",
    "AC_MAX_SAMPLE_GAP_MS",
    "AC_MOVEMENT_MAX_PING",
    "AC_MOVEMENT_BASE_SPEED",
    "AC_MOVEMENT_PING_TOLERANCE",
    "AC_MOVEMENT_MAX_PING_TOLERANCE",
    "AC_MOVEMENT_REQUIRED_SAMPLES",
    "AC_NETWORK_QUALITY_TTL_MS",
)


def load_constants(config_path: Path | None = None) -> dict[str, int | float]:
    """Read numeric thresholds from the Pawn config to reduce model drift."""
    path = config_path or ROOT / "include/ac/config.inc"
    source = path.read_text(encoding="utf-8")
    constants: dict[str, int | float] = {}

    for name in CONSTANT_NAMES:
        match = re.search(
            rf"^\s*#define\s+{re.escape(name)}\s+\(([-+]?\d+(?:\.\d+)?)\)\s*$",
            source,
            re.MULTILINE,
        )
        if not match:
            raise ValueError(f"Pawn configuration is missing numeric constant: {name}")
        raw = match.group(1)
        constants[name] = float(raw) if "." in raw else int(raw)

    return constants


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def validate_fixture(fixture: dict[str, Any]) -> None:
    """Validate the version-1 scenario/event structure before replay."""
    _require(fixture.get("schema_version") == 1, "schema_version must be 1")
    _require(isinstance(fixture.get("scenario_id"), str), "scenario_id must be a string")
    _require(bool(fixture["scenario_id"]), "scenario_id cannot be empty")
    _require(isinstance(fixture.get("description"), str), "description must be a string")
    _require(isinstance(fixture.get("events"), list), "events must be an array")
    _require(isinstance(fixture.get("expected"), dict), "expected must be an object")

    previous_time = -1
    allowed = {
        "connect",
        "disconnect",
        "load_begin",
        "load_complete",
        "grace_start",
        "movement_sample",
        "evidence",
    }

    for index, event in enumerate(fixture["events"]):
        _require(isinstance(event, dict), f"event {index} must be an object")
        event_type = event.get("type")
        _require(event_type in allowed, f"event {index} has unsupported type: {event_type}")
        at_ms = event.get("at_ms")
        _require(isinstance(at_ms, int) and not isinstance(at_ms, bool) and at_ms >= 0,
                 f"event {index} at_ms must be a non-negative integer")
        _require(at_ms >= previous_time, f"event {index} is out of timestamp order")
        previous_time = at_ms

        if event_type in {"load_begin", "load_complete"}:
            key = "account_id"
            _require(isinstance(event.get(key), int) and event[key] > 0,
                     f"event {index} {key} must be a positive integer")
        if event_type == "load_complete":
            _require(isinstance(event.get("session_token"), int),
                     f"event {index} session_token must be an integer")
            for key in ("score", "strikes", "strike_decay_at"):
                if key in event:
                    _require(isinstance(event[key], int) and event[key] >= 0,
                             f"event {index} {key} must be a non-negative integer")
        if event_type == "grace_start":
            _require(isinstance(event.get("duration_ms"), int) and event["duration_ms"] >= 0,
                     f"event {index} duration_ms must be a non-negative integer")
        if event_type == "movement_sample":
            for key in ("x", "y"):
                _require(isinstance(event.get(key), (int, float)), f"event {index} {key} must be numeric")
            _require(isinstance(event.get("ping"), int), f"event {index} ping must be an integer")
            _require(event.get("state", "onfoot") in {"onfoot", "driver", "passenger", "spectator", "dead"},
                     f"event {index} has an unsupported player state")
            for key in ("interior", "world"):
                _require(isinstance(event.get(key, 0), int), f"event {index} {key} must be an integer")
            loss = event.get("packet_loss")
            _require(loss is None or isinstance(loss, (int, float)),
                     f"event {index} packet_loss must be numeric or null")
            age = event.get("packet_loss_age_ms", 0)
            _require(isinstance(age, int) and age >= 0,
                     f"event {index} packet_loss_age_ms must be a non-negative integer")
        if event_type == "evidence":
            _require(event.get("category") in CATEGORY_IDS, f"event {index} has unknown evidence category")
            _require(isinstance(event.get("points"), int) and event["points"] > 0,
                     f"event {index} points must be a positive integer")


class ReplayEngine:
    """Reference implementation of the v1 movement, evidence and session contract."""

    def __init__(self, constants: dict[str, int | float] | None = None) -> None:
        self.c = constants or load_constants()
        self.session_token = 0
        self.connected = False
        self.account_id = 0
        self.loaded = False
        self.enabled = False
        self.load_completion_results: list[bool] = []

        self.last_update_tick = 0
        self.last_movement_tick = 0
        self.has_movement_sample = False
        self.last_x = 0.0
        self.last_y = 0.0
        self.last_interior = 0
        self.last_world = 0
        self.last_state = "onfoot"
        self.over_limit_samples = 0
        self.grace_started_tick = 0
        self.grace_duration_ms = 0

        self.category_last_at = {name: 0 for name in CATEGORY_IDS}
        self.last_strike_at = 0
        self.score = 0
        self.strikes = 0
        self.evidence_categories: list[str] = []
        self.movement_evidence = 0

    def _reset_session(self) -> None:
        self.account_id = 0
        self.loaded = False
        self.enabled = False
        self.grace_started_tick = 0
        self.grace_duration_ms = 0
        self.score = 0
        self.strikes = 0
        self.category_last_at = {name: 0 for name in CATEGORY_IDS}
        self.last_strike_at = 0
        self.evidence_categories = []
        self.movement_evidence = 0
        self._reset_sampling()

    def _reset_sampling(self) -> None:
        self.last_update_tick = 0
        self.last_movement_tick = 0
        self.has_movement_sample = False
        self.over_limit_samples = 0

    def _network_reliable(self, event: dict[str, Any]) -> bool:
        ping = event["ping"]
        if ping < 0 or ping == 65535 or ping > self.c["AC_MOVEMENT_MAX_PING"]:
            return False

        packet_loss = event.get("packet_loss")
        age = event.get("packet_loss_age_ms", 0)
        if (
            packet_loss is not None
            and age <= self.c["AC_NETWORK_QUALITY_TTL_MS"]
            and packet_loss >= 15.0
        ):
            return False
        return True

    def _record_evidence(self, category: str, points: int, at_ms: int) -> None:
        if not (self.connected and self.loaded and self.enabled):
            return
        now = at_ms // 1000
        last_at = self.category_last_at[category]
        if last_at > 0 and now - last_at < self.c["AC_CATEGORY_COOLDOWN_SECONDS"]:
            return

        recent = {
            name
            for name, timestamp in self.category_last_at.items()
            if timestamp > 0 and now - timestamp <= self.c["AC_EVIDENCE_WINDOW_SECONDS"]
        }
        other = recent - {category}
        adjusted_points = points + min(len(other) * 3, 9)
        self.category_last_at[category] = now
        self.evidence_categories.append(category)
        self.score = min(100, self.score + adjusted_points)

        threshold = self.c["AC_SCORE_STRIKE_THRESHOLD"]
        reduction = self.c["AC_SCORE_STRIKE_REDUCTION"]
        strike_cooldown = self.c["AC_STRIKE_COOLDOWN_SECONDS"]
        if (
            self.score >= threshold
            and bool(other)
            and (self.last_strike_at == 0 or now - self.last_strike_at >= strike_cooldown)
        ):
            self.strikes += 1
            self.last_strike_at = now
            self.score = max(0, self.score - reduction)

    def _movement_sample(self, event: dict[str, Any]) -> None:
        if not (self.connected and self.loaded and self.enabled):
            return
        tick = event["at_ms"]
        if tick - self.last_update_tick < self.c["AC_SAMPLE_INTERVAL_MS"]:
            return
        self.last_update_tick = tick

        if not self._network_reliable(event):
            self.has_movement_sample = False
            self.over_limit_samples = 0
            return

        state = event.get("state", "onfoot")
        if state == "driver":
            self.has_movement_sample = False
            self.over_limit_samples = 0
            return
        if state != "onfoot":
            self.has_movement_sample = False
            self.over_limit_samples = 0
            return

        x = float(event["x"])
        y = float(event["y"])
        interior = event.get("interior", 0)
        world = event.get("world", 0)

        if self.grace_duration_ms > 0 and tick - self.grace_started_tick < self.grace_duration_ms:
            self._set_movement_baseline(x, y, interior, world, state, tick)
            return

        if (
            not self.has_movement_sample
            or self.last_interior != interior
            or self.last_world != world
            or self.last_state != state
        ):
            self._set_movement_baseline(x, y, interior, world, state, tick)
            return

        elapsed = tick - self.last_movement_tick
        if elapsed < 250 or elapsed > self.c["AC_MAX_SAMPLE_GAP_MS"]:
            self._set_movement_baseline(x, y, interior, world, state, tick)
            return

        distance = math.hypot(x - self.last_x, y - self.last_y)
        speed = distance * (1000.0 / elapsed)
        ping = event["ping"]
        limit = self.c["AC_MOVEMENT_BASE_SPEED"] + (
            ping * self.c["AC_MOVEMENT_PING_TOLERANCE"]
        )
        limit = min(
            limit,
            self.c["AC_MOVEMENT_BASE_SPEED"] + self.c["AC_MOVEMENT_MAX_PING_TOLERANCE"],
        )

        if speed > limit:
            self.over_limit_samples += 1
            if self.over_limit_samples >= self.c["AC_MOVEMENT_REQUIRED_SAMPLES"]:
                self._record_evidence("movement", 14, tick)
                self.movement_evidence += 1
                self.over_limit_samples = 0
        else:
            self.over_limit_samples = 0

        self.last_x = x
        self.last_y = y
        self.last_movement_tick = tick

    def _set_movement_baseline(
        self, x: float, y: float, interior: int, world: int, state: str, tick: int
    ) -> None:
        self.last_x = x
        self.last_y = y
        self.last_movement_tick = tick
        self.last_interior = interior
        self.last_world = world
        self.last_state = state
        self.has_movement_sample = True
        self.over_limit_samples = 0

    def run(self, fixture: dict[str, Any]) -> dict[str, Any]:
        validate_fixture(fixture)
        for event in fixture["events"]:
            kind = event["type"]
            at_ms = event["at_ms"]

            if kind == "connect":
                self.session_token += 1
                self._reset_session()
                self.connected = True
            elif kind == "disconnect":
                self.session_token += 1
                self._reset_session()
                self.connected = False
            elif kind == "load_begin":
                if self.connected:
                    self.session_token += 1
                    self._reset_session()
                    self.account_id = event["account_id"]
            elif kind == "load_complete":
                accepted = (
                    event["session_token"] == self.session_token
                    and event["account_id"] == self.account_id
                    and self.connected
                    and not self.loaded
                )
                self.load_completion_results.append(accepted)
                if accepted:
                    self.loaded = True
                    self.enabled = True
                    self.score = min(100, event.get("score", 0))
                    self.strikes = event.get("strikes", 0)
                    strike_decay_at = event.get("strike_decay_at", 0)
                    now_seconds = at_ms // 1000
                    self.last_strike_at = 0
                    if (
                        self.strikes > 0
                        and strike_decay_at > 0
                        and strike_decay_at <= now_seconds
                        and now_seconds - strike_decay_at < self.c["AC_STRIKE_COOLDOWN_SECONDS"]
                    ):
                        self.last_strike_at = strike_decay_at
            elif kind == "grace_start":
                self.grace_started_tick = at_ms
                self.grace_duration_ms = event["duration_ms"]
                self._reset_sampling()
            elif kind == "movement_sample":
                self._movement_sample(event)
            elif kind == "evidence":
                self._record_evidence(event["category"], event["points"], at_ms)

        return {
            "evidence_count": min(8, len(self.evidence_categories)),
            "evidence_categories": self.evidence_categories,
            "movement_evidence": self.movement_evidence,
            "score": self.score,
            "strikes": self.strikes,
            "loaded": self.loaded,
            "account_id": self.account_id,
            "session_token": self.session_token,
            "load_completion_results": self.load_completion_results,
        }


def replay_file(path: Path) -> dict[str, Any]:
    fixture = json.loads(path.read_text(encoding="utf-8"))
    result = ReplayEngine().run(fixture)
    expected = fixture["expected"]
    for key, value in expected.items():
        actual = result.get(key)
        if actual != value:
            raise AssertionError(
                f"{fixture['scenario_id']}: expected {key}={value!r}, got {actual!r}"
            )
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--fixtures",
        type=Path,
        default=ROOT / "tests" / "fixtures",
        help="directory containing version-1 JSON replay fixtures",
    )
    args = parser.parse_args()

    fixture_paths = sorted(args.fixtures.glob("*.json"))
    if not fixture_paths:
        print(f"No replay fixtures found in {args.fixtures}", file=sys.stderr)
        return 2

    failures = 0
    for path in fixture_paths:
        try:
            result = replay_file(path)
            print(
                f"PASS {path.stem}: {result['evidence_count']} evidence, "
                f"{result['strikes']} strikes"
            )
        except (AssertionError, ValueError, OSError, json.JSONDecodeError) as error:
            failures += 1
            print(f"FAIL {path.stem}: {error}", file=sys.stderr)

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
