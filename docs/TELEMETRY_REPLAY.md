# Telemetry replay fixtures

## Purpose and trust boundary

The replay format is a deterministic, privacy-safe test input for the anti-cheat contract. It is intended for synthetic scenarios and reviewed, anonymised traces after sensitive identifiers and coordinates have been removed.

The Python replay engine is a reference model for the documented v1 rules. It reads numeric thresholds from `include/ac/config.inc`, but it does not execute Pawn bytecode or start open.mp. A passing replay validates the fixture and reference model, not live detector accuracy. Runtime, Android/desktop false-positive, performance, and adversarial validation remain separate release gates.

Never commit account names, IP addresses, session secrets, real player identifiers, or raw private chat into fixtures. Use relative coordinates, synthetic account IDs, and monotonic timestamps.

## Version 1 scenario shape

Each fixture is one UTF-8 JSON document:

```json
{
  "schema_version": 1,
  "scenario_id": "sustained_onfoot_speed_anomaly",
  "description": "Three valid over-limit samples emit movement evidence.",
  "events": [
    {
      "type": "movement_sample",
      "at_ms": 1000,
      "x": 0.0,
      "y": 0.0,
      "ping": 50,
      "packet_loss": 0.0,
      "state": "onfoot",
      "interior": 0,
      "world": 0
    }
  ],
  "expected": {
    "evidence_count": 0,
    "evidence_categories": [],
    "movement_evidence": 0,
    "score": 0,
    "strikes": 0
  }
}
```

All event timestamps are integer milliseconds on one monotonic timeline and must be non-decreasing. Fixture coordinates are relative, not world-specific. Supported event types are:

| Event | Required fields | Meaning |
| --- | --- | --- |
| `connect` / `disconnect` | `at_ms` | Advance the player-slot session token and reset session state. |
| `load_begin` | `at_ms`, `account_id` | Begin an account load and advance the session token. |
| `load_complete` | `at_ms`, `account_id`, `session_token` | Attempt to apply an asynchronous load result. |
| `grace_start` | `at_ms`, `duration_ms` | Mark a server-authoritative legal transition grace period. |
| `movement_sample` | `at_ms`, `x`, `y`, `ping` | Submit a synthetic movement sample with optional network/state context. |
| `evidence` | `at_ms`, `category`, `points` | Inject detector-family evidence to test correlation policy. |

Optional movement fields are `packet_loss`, `packet_loss_age_ms`, `state`, `interior`, and `world`. A null or omitted packet-loss value means unknown. A measurement older than the configured network-quality TTL is ignored. The replay reads numeric sampling and threshold values from the Pawn configuration.

The `expected` object asserts exact output fields and can include `evidence_count`, `evidence_categories`, `movement_evidence`, `score`, `strikes`, `loaded`, `account_id`, `session_token`, and `load_completion_results`.

## Run locally or in CI

From the repository root:

```sh
python3 tools/anticheat/replay.py
python3 -m unittest discover -s tests -v
```

The replay command prints one PASS/FAIL line per fixture. The unittest suite also checks timestamp ordering, schema rejection, source-derived thresholds, and important source-contract gates.

## Current fixture coverage

- Legal on-foot movement during and after a grace window.
- Sustained movement anomaly requiring consecutive valid samples.
- High packet loss, ping 65535, and over-limit ping resetting movement streaks.
- Long sample gaps and virtual-world changes establishing a fresh baseline.
- Single-family evidence exceeding the score threshold without a strike.
- Cross-family evidence correlation creating a review strike.
- Expired packet-loss measurements no longer suppressing samples.
- Stale asynchronous account-load results and duplicate completions being rejected.
- Persisted strike cooldown remaining active after disconnect, player-slot reuse, and account reload.

Add a fixture whenever a threshold or suppressor changes. Update expected values only after reviewing the rule change; never change expected values merely to silence a failing test.
