#!/usr/bin/env python3
"""Tests for the privacy-safe local staging log exporter."""

from __future__ import annotations

import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from io import StringIO
from contextlib import redirect_stderr, redirect_stdout

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools" / "anticheat"))

from staging_log_sanitize import main, sanitize_capture  # noqa: E402

FIXTURE = ROOT / "tests" / "fixtures" / "staging_acceptance_success.log"


def vehicle_line(interval: int, speed: int = 1200) -> str:
    return (
        "[AC-STAGE-VEHICLE] schema=2 actor=primary "
        f"sample_interval_ms={interval} model=411 speed_centi_kmh={speed} "
        "ping=55 packet_loss_centi_pct=-1"
    )


def source_capture() -> bytes:
    """Make a complete synthetic run with private console noise and timed telemetry."""
    lines = FIXTURE.read_text(encoding="utf-8").splitlines()
    run_end = next(index for index, line in enumerate(lines) if "event=run_end" in line)
    lines[run_end:run_end] = [vehicle_line(0), vehicle_line(500, 1800)]
    return (
        "server started on 192.0.2.44; private host metadata\n"
        "connected player=Example; remote=198.51.100.22\n"
        + "\n".join(lines)
        + "\nserver shutdown with unrelated diagnostic data\n"
    ).encode("utf-8")


class StagingLogSanitizeTests(unittest.TestCase):
    def test_export_keeps_only_valid_structured_records(self) -> None:
        payload, summary = sanitize_capture(source_capture())
        exported = payload.decode("utf-8")

        self.assertIn("[AC-STAGE-EVENT] schema=1 event=run_begin", exported)
        self.assertIn("[AC-STAGE-EVENT] schema=1 event=run_end", exported)
        self.assertIn("sample_interval_ms=500", exported)
        self.assertNotIn("192.0.2.44", exported)
        self.assertNotIn("198.51.100.22", exported)
        self.assertNotIn("Example", exported)
        self.assertEqual(summary["event_record_count"], len([
            line for line in exported.splitlines() if "[AC-STAGE-EVENT] " in line
        ]))
        self.assertEqual(summary["vehicle_sample_count"], 2)
        self.assertEqual(summary["output_bytes"], len(payload))
        self.assertEqual(len(summary["sha256"]), 64)

    def test_export_rejects_incomplete_capture(self) -> None:
        lines = source_capture().decode("utf-8").splitlines()
        lines = [line for line in lines if "event=run_end" not in line]
        with self.assertRaisesRegex(ValueError, "run_end marker is missing"):
            sanitize_capture(("\n".join(lines) + "\n").encode("utf-8"))

    def test_export_rejects_event_records_after_run_end(self) -> None:
        raw = source_capture() + (
            "[AC-STAGE-EVENT] schema=1 event=teleport actor=primary\n"
        ).encode("utf-8")
        with self.assertRaisesRegex(ValueError, "event found after run_end"):
            sanitize_capture(raw)

    def test_export_rejects_malformed_vehicle_telemetry(self) -> None:
        raw = source_capture().replace(
            b"sample_interval_ms=500",
            b"sample_interval_ms=499",
        )
        with self.assertRaisesRegex(ValueError, "at least 500"):
            sanitize_capture(raw)

    def test_export_rejects_unexpected_event_fields(self) -> None:
        raw = source_capture().replace(
            b"event=teleport actor=primary",
            b"event=teleport actor=primary playerid=7",
        )
        with self.assertRaisesRegex(ValueError, "unsupported field playerid"):
            sanitize_capture(raw)

    def test_cli_creates_private_new_file_and_refuses_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "raw-console.log"
            output = root / "sanitized.log"
            source.write_bytes(source_capture())

            stdout = StringIO()
            with redirect_stdout(stdout):
                self.assertEqual(main(["--log", str(source), "--output", str(output)]), 0)

            self.assertTrue(output.is_file())
            self.assertNotIn("192.0.2.44", output.read_text(encoding="utf-8"))
            self.assertIn("Output SHA-256:", stdout.getvalue())
            self.assertEqual(output.stat().st_mode & 0o777, 0o600)

            with redirect_stderr(StringIO()):
                self.assertEqual(main(["--log", str(source), "--output", str(output)]), 2)

    def test_cli_rejects_same_source_and_output_path(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "same.log"
            path.write_bytes(source_capture())
            with redirect_stderr(StringIO()):
                self.assertEqual(main(["--log", str(path), "--output", str(path)]), 2)

    def test_cli_rejects_source_symlinks(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "raw.log"
            link = root / "source-link.log"
            output = root / "sanitized.log"
            source.write_bytes(source_capture())
            link.symlink_to(source)
            with redirect_stderr(StringIO()):
                self.assertEqual(main(["--log", str(link), "--output", str(output)]), 2)
            self.assertFalse(output.exists())

    def test_cli_rejects_source_replaced_with_symlink_during_open(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "raw.log"
            target = root / "private-target.log"
            output = root / "sanitized.log"
            source.write_bytes(source_capture())
            target.write_bytes(b"private target must not be read")
            real_open = os.open

            def replace_source_before_open(path_arg, flags, mode=0o777):
                if Path(path_arg) == source:
                    source.unlink()
                    source.symlink_to(target)
                return real_open(path_arg, flags, mode)

            with patch("staging_log_sanitize.os.open", side_effect=replace_source_before_open):
                with redirect_stderr(StringIO()):
                    self.assertEqual(main(["--log", str(source), "--output", str(output)]), 2)

            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
