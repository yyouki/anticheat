# Validation gates

## Current repository validation

The most recent PR #2 workflow at head commit `4484a25b5b320d1c953e964a87e83dde84a1e75f` was GitHub Actions run #31:

- Static repository audit: PASSED.
- Default Pawn smoke compile: PASSED.
- Opt-in feature-gate Pawn smoke compile: PASSED.
- Python unit tests: FAILED before the follow-up fix. The replay loader searched for `AC_NETWORK_QUALITY_TTL_MS` only in `include/ac/config.inc`, although the constant is defined in `include/ac/network.inc`.
- Replay fixture command: SKIPPED because the unit-test step failed.

The current follow-up PR fixes the source-file lookup and isolates schema validation from replay-model initialization. Its CI result must be checked before treating the Python validation gate as passed.

The compile result proves source/include compatibility for the smoke gamemode. It does not prove runtime correctness, detector accuracy, resistance to bypasses, or production performance.

## Required release suite

| Area | Required cases |
| --- | --- |
| Lifecycle | connect, login, character selection, spawn, death, disconnect, reconnect, player ID reuse |
| Legal movement | admin teleport, jail/release, house/business/interior transitions, world changes, hospital delivery, scripted movement |
| State | on-foot, driver, passenger, spectating, spawn/death transitions, parachute and falling |
| Vehicle | car, bike, truck, special vehicles, aircraft, boats, trains, collision impulse, vehicle switching |
| Network | low/high ping, initial 65535 ping, jitter, packet loss, delayed callbacks, low FPS |
| Clients | supported desktop and Android client builds, touch/controller input, reconnect and missing integrity response |
| Combat | damage callback ordering, lag compensation, melee, splash, multi-target, ordinary burst firing and high ping |
| Adversarial | slow/gradual speed changes, alternating values around threshold, single-category spam, cross-category bursts, reconnect persistence |
| Admin | permission checks, evidence view, reset audit callback, offline account persistence |
| Persistence | stale async load token, account ID mismatch, absent adapter, transient save failure, server restart |

## Performance methodology

Benchmark baseline and enabled builds at 1, 25, 50 and expected peak player count. Record average and p95 server tick duration, CPU, memory, number of sampled players, SQL requests from the host adapter, and evidence callback volume. Sampling is capped at 2 Hz per enabled player and uses no per-player timer.

Reject the release if the agreed tick-time or CPU budget is exceeded. Do not infer performance from the number of Pawn statements or from a local compiler run.

## Adversarial review

A reviewer must attempt gradual threshold evasion, single-family evidence flooding, alternating below/above-threshold movement, stale client synchronization, delayed callback delivery, high packet loss, player-slot reuse during async persistence, and legitimate script transitions. Every claimed detection must include an evidence explanation, and every suppressor must have tests showing that it does not hide unrelated detectors.

## Promotion policy

No automatic punishment in v1. A production release requires a successful build, passing runtime/false-positive/performance/adversarial tests, a reviewed adapter implementation, and an administrator-visible evidence trail.
