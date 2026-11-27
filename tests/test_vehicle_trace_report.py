#!/usr/bin/env python3
"""Tests for the local privacy-safe vehicle trace summarizer."""

from __future__ import annotations

from contextlib import redirect_stdout
import json
from io import StringIO
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools" / "anticheat"))
from vehicle_trace_report import (  # noqa: E402
    build_report,
    main,
    parse_vehicle_observations,
)


def line(
    model: int = 411,
    speed: int = 1234,
    ping: int = 50,
    packet_loss: int = -1,
) -> str:
    return (
        "[AC-STAGE-VEHICLE] schema=1 actor=primary "
        f"model={model} speed_centi_kmh={speed} ping={ping} "
        f"packet_loss_centi_pct={packet_loss}"
    )


class VehicleTraceReportTests(unittest.TestCase):
    def test_parse_and_group_observations_by_model(self) -> None:
        samples = parse_vehicle_observations([
            "[AC-STAGE] ordinary server output",
            line(411, 1000, 40, 0),
            line(411, 2000, 60, 150),
            line(560, 3000, 80, -1),
        ])
        self.assertEqual(len(samples), 3)
        report = build_report(samples)
        self.assertEqual(report["sample_count"], 3)
        self.assertEqual(set(report["models"]), {"411", "560"})
        self.assertEqual(report["models"]["411"]["sample_count"], 2)
        self.assertEqual(
            report["models"]["411"]["speed_kmh"],
            {"min": 10.0, "p50": 10.0, "p95": 20.0, "max": 20.0},
        )
        self.assertEqual(report["models"]["411"]["packet_loss_known_samples"], 2)

    def test_ignores_acceptance_events_and_unrelated_console_lines(self) -> None:
        samples = parse_vehicle_observations([
            "[AC-STAGE-EVENT] schema=1 event=vehicle_enter actor=primary",
            "[AC-STAGE] connected to server",
        ])
        self.assertEqual(samples, [])
        self.assertEqual(build_report(samples)["status"], "empty")

    def test_unknown_fields_are_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "unsupported field playerid"):
            parse_vehicle_observations([line() + " playerid=7"])

    def test_duplicate_fields_are_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "duplicate field model"):
            parse_vehicle_observations([line() + " model=411"])

    def test_missing_fields_are_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "missing required"):
            parse_vehicle_observations([
                "[AC-STAGE-VEHICLE] schema=1 actor=primary model=411 ping=50"
            ])

    def test_schema_and_actor_are_strict(self) -> None:
        with self.assertRaisesRegex(ValueError, "unsupported schema"):
            parse_vehicle_observations([line().replace("schema=1", "schema=2")])
        with self.assertRaisesRegex(ValueError, "primary test role"):
            parse_vehicle_observations([line().replace("actor=primary", "actor=secondary")])

    def test_model_and_ping_bounds_are_checked(self) -> None:
        with self.assertRaisesRegex(ValueError, "vehicle ID range"):
            parse_vehicle_observations([line(model=399)])
        with self.assertRaisesRegex(ValueError, "ping exceeds"):
            parse_vehicle_observations([line(ping=65536)])

    def test_speed_and_packet_loss_bounds_are_checked(self) -> None:
        with self.assertRaisesRegex(ValueError, "speed_centi_kmh exceeds"):
            parse_vehicle_observations([line(speed=1_000_001)])
        with self.assertRaisesRegex(ValueError, "packet loss exceeds"):
            parse_vehicle_observations([line(packet_loss=10_001)])
        with self.assertRaisesRegex(ValueError, "packet_loss_centi_pct must be"):
            parse_vehicle_observations([line(packet_loss=-2)])

    def test_malformed_numeric_values_are_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "non-negative integer"):
            parse_vehicle_observations([line(speed=-1)])
        with self.assertRaisesRegex(ValueError, "non-negative integer"):
            parse_vehicle_observations([line().replace("ping=50", "ping=+50")])

    def test_report_never_claims_runtime_or_envelope_validation(self) -> None:
        report = build_report(parse_vehicle_observations([line()]))
        self.assertEqual(report["validation_scope"], "descriptive_server_side_staging_observations")
        self.assertEqual(
            report["runtime_validation"],
            {
                "log_origin_authenticated": False,
                "detector_accuracy_verified": False,
                "safe_speed_envelope_established": False,
                "production_ready": False,
            },
        )
        serialized = json.dumps(report, sort_keys=True).lower()
        self.assertNotIn("playerid", serialized)
        self.assertNotIn("accountid", serialized)
        self.assertNotIn("vehicleid", serialized)

    def test_cli_outputs_json_without_private_paths(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            log_path = Path(directory) / "server.log"
            log_path.write_text(line() + "\n", encoding="utf-8")
            output = StringIO()
            with patch("sys.argv", ["vehicle_trace_report.py", "--log", str(log_path), "--json"]):
                with redirect_stdout(output):
                    exit_code = main()
            self.assertEqual(exit_code, 0)
            payload = json.loads(output.getvalue())
            self.assertEqual(payload["sample_count"], 1)
            self.assertNotIn(directory, output.getvalue())

    def test_cli_rejects_symlink_input(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "server.log"
            link = Path(directory) / "server-link.log"
            target.write_text(line() + "\n", encoding="utf-8")
            link.symlink_to(target)
            with patch("sys.argv", ["vehicle_trace_report.py", "--log", str(link)]):
                with redirect_stdout(StringIO()), redirect_stdout(StringIO()):
                    exit_code = main()
            self.assertEqual(exit_code, 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
