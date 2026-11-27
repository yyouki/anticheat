#!/usr/bin/env python3
"""Tests for descriptive and review-bound vehicle trace summaries."""

from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
import copy
import hashlib
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
    ALLOWED_TRACE_MODELS,
    _load_bound_traces,
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


def create_bound_capture(
    directory: Path,
    *,
    model: int = 411,
    speed: int = 1234,
    run_id: str = "run-001",
    network_profile: str = "stable",
    client_build: str = "test-build-1",
    filename: str | None = None,
) -> tuple[Path, Path]:
    """Create a synthetic passing staging capture and matching schema-v2 review."""
    fixture = ROOT / "tests" / "fixtures" / "staging_acceptance_success.log"
    raw = fixture.read_bytes() + b"\n" + (line(model=model, speed=speed) + "\n").encode("utf-8")
    file_stem = filename or run_id
    capture_path = directory / f"{file_stem}.log"
    capture_path.write_bytes(raw)

    template_path = ROOT / "docs" / "templates" / "staging-review-template.json"
    record = json.loads(template_path.read_text(encoding="utf-8"))
    record["run_id"] = run_id
    record["environment"].update({
        "server_commit": "a" * 40,
        "staging_artifact_sha256": "b" * 64,
        "capture_sha256": hashlib.sha256(raw).hexdigest(),
        "openmp_version": "v1.6.7.3218",
        "client_platform": "android",
        "client_build": client_build,
        "network_profile": network_profile,
        "started_at": "2026-11-27T12:00:00+00:00",
    })
    for observation in record["observations"]:
        observation["result"] = "clean"
        observation["evidence_categories"] = []
        observation["review_decision"] = "not_applicable"
        observation["block_reason"] = None
        if observation["scenario_id"] == "spectate_roundtrip":
            observation["secondary_client_connected"] = True

    record_path = directory / f"{file_stem}.json"
    record_path.write_text(json.dumps(record, indent=2), encoding="utf-8")
    return capture_path, record_path


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
        with self.assertRaisesRegex(ValueError, "not approved"):
            parse_vehicle_observations([line(model=417)])
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
        self.assertEqual(report["provenance"]["binding_status"], "not_provided")
        self.assertEqual(
            report["runtime_validation"],
            {
                "capture_file_binding_verified": False,
                "log_origin_authenticated": False,
                "operator_scenario_execution_verified": False,
                "detector_accuracy_verified": False,
                "safe_speed_envelope_established": False,
                "production_ready": False,
            },
        )
        serialized = json.dumps(report, sort_keys=True).lower()
        self.assertNotIn("playerid", serialized)
        self.assertNotIn("accountid", serialized)
        self.assertNotIn("vehicleid", serialized)

    def test_staging_trace_model_allowlist_excludes_special_vehicle_models(self) -> None:
        from replay import load_excluded_vehicle_models

        staging = (ROOT / "examples" / "staging.pwn").read_text(encoding="utf-8")
        start = staging.index("stock bool:AC_StageIsTraceVehicleModel(")
        opening = staging.index("{", start)
        depth = 0
        for index in range(opening, len(staging)):
            if staging[index] == "{":
                depth += 1
            elif staging[index] == "}":
                depth -= 1
                if depth == 0:
                    body = staging[opening + 1:index]
                    break
        else:
            self.fail("unterminated AC_StageIsTraceVehicleModel function")

        allowed = {
            int(value)
            for value in __import__("re").findall(r"\b(\d{3})\b", body)
        }
        self.assertGreaterEqual(len(allowed), 30)
        self.assertTrue(all(400 <= model <= 611 for model in allowed))
        self.assertEqual(allowed, set(ALLOWED_TRACE_MODELS))
        self.assertTrue(allowed.isdisjoint(load_excluded_vehicle_models()))

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
            self.assertFalse(payload["runtime_validation"]["capture_file_binding_verified"])

    def test_cli_combines_multiple_unbound_logs_by_model(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            first = Path(directory) / "model-411.log"
            second = Path(directory) / "model-560.log"
            first.write_text(line(411, 1000, 40, 0) + "\n", encoding="utf-8")
            second.write_text(line(560, 2500, 70, -1) + "\n", encoding="utf-8")
            output = StringIO()
            with patch(
                "sys.argv",
                ["vehicle_trace_report.py", "--log", str(first), "--log", str(second), "--json"],
            ):
                with redirect_stdout(output):
                    exit_code = main()
            self.assertEqual(exit_code, 0)
            report = json.loads(output.getvalue())
            self.assertEqual(report["sample_count"], 2)
            self.assertEqual(set(report["models"]), {"411", "560"})
            self.assertEqual(report["models"]["560"]["speed_kmh"]["max"], 25.0)

    def test_cli_rejects_combined_logs_over_total_byte_limit(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            first = Path(directory) / "first.log"
            second = Path(directory) / "second.log"
            first.write_text(line() + "\n", encoding="utf-8")
            second.write_text(line(560) + "\n", encoding="utf-8")
            output = StringIO()
            error_output = StringIO()
            with patch("vehicle_trace_report.MAX_TOTAL_LOG_BYTES", 1):
                with patch(
                    "sys.argv",
                    ["vehicle_trace_report.py", "--log", str(first), "--log", str(second)],
                ):
                    with redirect_stdout(output), redirect_stderr(error_output):
                        exit_code = main()
            self.assertEqual(exit_code, 2)
            self.assertIn("combined logs exceed", error_output.getvalue())

    def test_cli_rejects_duplicate_unbound_capture(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            log_path = Path(directory) / "server.log"
            log_path.write_text(line() + "\n", encoding="utf-8")
            with patch("sys.argv", ["vehicle_trace_report.py", "--log", str(log_path), "--log", str(log_path)]):
                with redirect_stderr(StringIO()):
                    self.assertEqual(main(), 2)

    def test_cli_rejects_symlink_input(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "server.log"
            link = Path(directory) / "server-link.log"
            target.write_text(line() + "\n", encoding="utf-8")
            link.symlink_to(target)
            with patch("sys.argv", ["vehicle_trace_report.py", "--log", str(link)]):
                with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
                    exit_code = main()
            self.assertEqual(exit_code, 2)

    def test_bound_capture_verifies_sha256_and_environment(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            log_path, record_path = create_bound_capture(Path(directory))
            samples, provenance = _load_bound_traces([log_path], [record_path])
            report = build_report(samples, provenance)
            self.assertEqual(len(samples), 1)
            self.assertEqual(report["provenance"]["binding_status"], "verified")
            self.assertEqual(report["provenance"]["review_record_count"], 1)
            self.assertEqual(report["provenance"]["source_runs"][0]["run_id"], "run-001")
            self.assertEqual(report["provenance"]["environment"]["client_platform"], "android")
            self.assertTrue(report["runtime_validation"]["capture_file_binding_verified"])
            self.assertFalse(report["runtime_validation"]["log_origin_authenticated"])
            self.assertFalse(report["runtime_validation"]["operator_scenario_execution_verified"])

    def test_bound_capture_rejects_digest_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            log_path, record_path = create_bound_capture(Path(directory))
            record = json.loads(record_path.read_text(encoding="utf-8"))
            record["environment"]["capture_sha256"] = "0" * 64
            record_path.write_text(json.dumps(record), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "failed exact capture binding"):
                _load_bound_traces([log_path], [record_path])

    def test_bound_capture_rejects_unexecuted_vehicle_scenario(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            log_path, record_path = create_bound_capture(Path(directory))
            record = json.loads(record_path.read_text(encoding="utf-8"))
            vehicle_observation = next(
                item for item in record["observations"]
                if item["scenario_id"] == "vehicle_enter_drive_exit"
            )
            vehicle_observation["result"] = "not_run"
            record_path.write_text(json.dumps(record), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "must be recorded as clean"):
                _load_bound_traces([log_path], [record_path])

    def test_bound_capture_requires_matching_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first_log, first_record = create_bound_capture(root, run_id="run-001")
            second_log, second_record = create_bound_capture(
                root,
                model=560,
                run_id="run-002",
                network_profile="high_ping",
            )
            with self.assertRaisesRegex(ValueError, "mismatched server"):
                _load_bound_traces(
                    [first_log, second_log],
                    [first_record, second_record],
                )

    def test_bound_capture_requires_one_vehicle_model_per_log(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            log_path, record_path = create_bound_capture(root)
            raw = log_path.read_bytes() + (line(model=560) + "\n").encode("utf-8")
            log_path.write_bytes(raw)
            record = json.loads(record_path.read_text(encoding="utf-8"))
            record["environment"]["capture_sha256"] = hashlib.sha256(raw).hexdigest()
            record_path.write_text(json.dumps(record), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "exactly one approved vehicle model"):
                _load_bound_traces([log_path], [record_path])

    def test_bound_capture_rejects_duplicate_run_ids(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first_log, first_record = create_bound_capture(root, run_id="run-001", speed=1000)
            second_log, second_record = create_bound_capture(
                root, run_id="run-001", speed=2000, filename="second-run-file"
            )
            with self.assertRaisesRegex(ValueError, "duplicate review run ID"):
                _load_bound_traces([first_log, second_log], [first_record, second_record])

    def test_bound_capture_rejects_duplicate_capture_digest(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            log_path, record_path = create_bound_capture(root, run_id="run-001")
            record = json.loads(record_path.read_text(encoding="utf-8"))
            duplicate_record = copy.deepcopy(record)
            duplicate_record["run_id"] = "run-002"
            duplicate_path = root / "run-002.json"
            duplicate_path.write_text(json.dumps(duplicate_record), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "duplicate capture digest"):
                _load_bound_traces(
                    [log_path, log_path],
                    [record_path, duplicate_path],
                )

    def test_bound_capture_requires_one_record_per_log(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first_log, first_record = create_bound_capture(root, run_id="run-001")
            second_log, _ = create_bound_capture(root, model=560, run_id="run-002")
            with self.assertRaisesRegex(ValueError, "exactly one --record"):
                _load_bound_traces([first_log, second_log], [first_record])

    def test_bound_capture_rejects_review_record_symlink(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            log_path, record_path = create_bound_capture(root)
            link_path = root / "review-link.json"
            link_path.symlink_to(record_path)
            with self.assertRaisesRegex(ValueError, "review record must not be a symlink"):
                _load_bound_traces([log_path], [link_path])

    def test_cli_supports_one_to_one_bound_log_and_review_arguments(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            log_path, record_path = create_bound_capture(Path(directory))
            output = StringIO()
            with patch(
                "sys.argv",
                [
                    "vehicle_trace_report.py",
                    "--log", str(log_path),
                    "--record", str(record_path),
                    "--json",
                ],
            ):
                with redirect_stdout(output):
                    exit_code = main()
            self.assertEqual(exit_code, 0)
            report = json.loads(output.getvalue())
            self.assertEqual(report["provenance"]["binding_status"], "verified")
            self.assertEqual(report["sample_count"], 1)
            self.assertNotIn(directory, output.getvalue())


if __name__ == "__main__":
    unittest.main(verbosity=2)
