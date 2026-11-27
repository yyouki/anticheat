#!/usr/bin/env python3
"""Source-contract tests for the optional versioned evidence callbacks."""

from __future__ import annotations

from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


class EvidenceCallbackContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.state = (ROOT / "include" / "ac" / "state.inc").read_text(encoding="utf-8")
        cls.evidence = (ROOT / "include" / "ac" / "evidence.inc").read_text(encoding="utf-8")
        cls.core = (ROOT / "include" / "ac" / "core.inc").read_text(encoding="utf-8")
        cls.smoke = (ROOT / "examples" / "smoke.pwn").read_text(encoding="utf-8")
        cls.integration = (ROOT / "docs" / "INTEGRATION.md").read_text(encoding="utf-8")

    def test_v2_callback_forwards_are_declared(self) -> None:
        self.assertIn(
            "forward AC_OnEvidenceV2(playerid, accountid, sessiontoken, sequence, timestamp, category, points, ping, const reason[], Float:metric);",
            self.core,
        )
        self.assertIn(
            "forward AC_OnStrikeV2(playerid, accountid, sessiontoken, sequence, timestamp, strikes, const reason[]);",
            self.core,
        )

    def test_evidence_sequence_is_session_scoped(self) -> None:
        self.assertIn("new AC_EvidenceSequence[MAX_PLAYERS];", self.state)
        reset_player = self.state.split("stock AC_ResetPlayer(playerid)", 1)[1]
        self.assertIn("AC_EvidenceSequence[playerid] = 0;", reset_player)
        reset_evidence = self.state.split("stock AC_ResetEvidence(playerid)", 1)[1].split(
            "stock AC_ResetPlayer(playerid)", 1
        )[0]
        self.assertNotIn("AC_EvidenceSequence[playerid]", reset_evidence)
        self.assertIn("AC_EvidenceSequence[playerid]++", self.evidence)
        self.assertIn("if (AC_EvidenceSequence[playerid] <= 0)", self.evidence)

    def test_v2_payloads_include_event_context_and_exact_format_arity(self) -> None:
        evidence_call = re.search(
            r'CallLocalFunction\("AC_OnEvidenceV2",\s*"([d]+sf)"',
            self.evidence,
        )
        self.assertIsNotNone(evidence_call)
        self.assertEqual(evidence_call.group(1), "ddddddddsf")
        self.assertRegex(
            self.evidence,
            r'playerid, accountid, sessiontoken, evidence_sequence, now,\s*'
            r'category, adjusted_points, ping, reason, metric',
        )

        strike_call = re.search(
            r'CallLocalFunction\("AC_OnStrikeV2",\s*"([d]+s)"',
            self.evidence,
        )
        self.assertIsNotNone(strike_call)
        self.assertEqual(strike_call.group(1), "dddddds")
        self.assertRegex(
            self.evidence,
            r'playerid, accountid, sessiontoken, evidence_sequence, now,\s*'
            r'AC_StrikeCount\[playerid\], reason',
        )

    def test_legacy_callbacks_remain_unchanged(self) -> None:
        self.assertIn('CallLocalFunction("AC_OnEvidence", "ddddsf"', self.evidence)
        self.assertIn('CallLocalFunction("AC_OnStrike", "ddds"', self.evidence)
        self.assertIn(
            "public AC_OnEvidence(playerid, category, points, ping, const reason[], Float:metric)",
            self.smoke,
        )
        self.assertIn(
            "public AC_OnStrike(playerid, accountid, strikes, const reason[])",
            self.smoke,
        )

    def test_smoke_gamemode_implements_both_v2_signatures(self) -> None:
        self.assertIn(
            "public AC_OnEvidenceV2(playerid, accountid, sessiontoken, sequence, timestamp, category, points, ping, const reason[], Float:metric)",
            self.smoke,
        )
        self.assertIn(
            "public AC_OnStrikeV2(playerid, accountid, sessiontoken, sequence, timestamp, strikes, const reason[])",
            self.smoke,
        )

    def test_host_guidance_covers_timestamp_sequence_and_storage_ownership(self) -> None:
        for phrase in (
            "Unix time in seconds",
            "not a globally unique database key",
            "not an authentication credential",
            "host should assign its own durable event ID",
            "bounded queue",
            "does not impose a database schema",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, self.integration)


if __name__ == "__main__":
    unittest.main(verbosity=2)
