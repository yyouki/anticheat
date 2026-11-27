# Validation gates

## Current repository validation

- Static repository audit: PASSED in GitHub Actions run #14.
- Default Pawn smoke compile: PASSED with Pawn compiler 3.10.11 and open.mp standard includes pinned to commit 17c1b0191195cb0b59a820135fbca622c84129dd. The default smoke AMX was produced.
- Opt-in feature-gate smoke compile: PASSED in run #14. The compile-only fixture enables the experimental combat cadence branch; it does not enable that detector in the default sample or prove runtime accuracy.
- Runtime test server: not run.
- Desktop/mobile false-positive suite: not run.
- Performance measurements: not run.
- Independent adversarial review: not run.
- Deterministic telemetry contract replays: pending first CI run. These are reference-model tests, not Pawn runtime tests.
- Reconnect strike-cooldown restoration: regression fixture added; awaiting CI verification.

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
