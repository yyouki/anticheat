# Validation gates

## Current repository validation

PR #3 fixed the replay-loader regression introduced in PR #2 and is now merged to `main`.

Post-merge GitHub Actions run #37 (`45946672307`) for merge commit `5bf1443a87ec132ba6d93655b45f4b89427fa2e8` completed successfully:

- Static repository audit: PASSED (31 required files).
- Python unit tests: PASSED (5 tests).
- Deterministic telemetry replay: PASSED (all 10 fixtures).
- Default Pawn smoke compile: PASSED with Pawn compiler 3.10.11 and open.mp standard includes pinned to commit `17c1b0191195cb0b59a820135fbca622c84129dd`.
- Opt-in feature-gate Pawn smoke compile: PASSED.

These checks validate static repository invariants, the Python reference contract, and compiler/include compatibility for the smoke gamemodes. They do not prove live detector accuracy, runtime correctness, resistance to bypasses, or production performance.

PR #4 adds an isolated staging gamemode, a volatile in-memory persistence adapter, a compiled staging package, and a headless open.mp boot smoke against pinned server release `v1.6.7.3218`.

The latest PR #4 head commit `b830c90509c38e64da977b34e664c4da75854a6b` passed GitHub Actions run #43 (`45949652586`):

- Static repository audit: PASSED (35 required files).
- Python unit tests: PASSED (7 tests).
- Existing deterministic telemetry replay: PASSED (all 10 fixtures).
- Default Pawn smoke compile: PASSED.
- Opt-in feature-gate Pawn smoke compile: PASSED.
- Staging gamemode Pawn compile: PASSED without compiler warnings.
- Staging package: uploaded as `ac-staging-package` (artifact ID `15176187949`).
- Headless open.mp runtime: PASSED; official pinned Linux x86 server `v1.6.7.3218` started and emitted the staging gamemode initialization marker.

This headless boot check proves that the server process can start and load the staging AMX. It does not connect a game client, exercise live player callbacks, validate anti-cheat thresholds, or establish mobile/desktop false-positive rates. Interactive player testing remains outstanding.

PR #4 was merged to `main` as commit `c0591531c02dc7829e5b0964081f8d177c2d100b`. Post-merge run #46 (`45951716621`) passed static audit, Python tests/replay, all three Pawn compile targets, artifact upload, and the headless open.mp boot.

PR #5 adds the in-server `/acstagetest` command. Its final PR head `345f4cd5a9743c82a47b9c13706d0cb9f039b70f` passed run #51 (`45955418806`):

- Static repository audit: PASSED (35 required files).
- Python unit tests: PASSED (8 tests).
- Deterministic telemetry replay: PASSED (all 10 fixtures).
- Default, opt-in feature-gate, and staging Pawn compiles: PASSED without Pawn compiler diagnostics.
- Staging package upload: PASSED (artifact ID `15178342714`).
- Pinned open.mp `v1.6.7.3218` headless boot: PASSED.

The `/acstagetest` command itself is compiled and source-contract checked in CI but is not invoked by the headless job because that job does not connect a game client. Its in-server runtime assertions still need to be run on a private staging server by connecting a player and issuing the command. The command simulates framework session reset functions; it does not replace a real network reconnect.

PR #5 was merged to `main` as `60a9b4d080034be41613959c369c8af1fcdef8d0`. Post-merge Actions run #52 (`45956905920`) completed successfully on that commit:

- Static repository audit: PASSED (35 required files).
- Python unit tests: PASSED (8 tests).
- Deterministic telemetry replay: PASSED (all 10 fixtures).
- Default, opt-in feature-gate, and staging Pawn compiles: PASSED.
- Staging package: uploaded as `ac-staging-package` (artifact ID `15178982257`).
- Pinned open.mp `v1.6.7.3218` headless boot: PASSED.

This remains a headless gamemode-load result. It does not execute `/acstagetest` or connect a game client.



PR #6 adds explicit server-owned interior, virtual-world, and spectating notifications. Its tested head `5cde5fa8b368ae93f31794f6a346b768489eaa03` passed GitHub Actions run #54 (`45957558835`):

- Static repository audit: PASSED (35 required files).
- Python unit tests: PASSED (9 tests).
- Deterministic telemetry replay: PASSED (all 10 fixtures).
- Default, opt-in feature-gate, and staging Pawn compiles: PASSED.
- Staging package upload: PASSED (`ac-staging-package`, artifact ID `15178978161`).
- Pinned open.mp `v1.6.7.3218` headless boot: PASSED.

These checks verify compilation, source contracts, and gamemode startup. They do not execute `/acstagetest` with a connected client or prove that actual live interior/world/spectating transitions are false-positive free.

PR #6 was merged to `main` as `003793945a546c8eb25b67c8036ad19cf633301e`. Post-merge Actions run #56 (`45959927009`) completed successfully:

- Static repository audit: PASSED (35 required files).
- Python unit tests and telemetry replay: PASSED.
- Default, opt-in feature-gate, and staging Pawn compiles: PASSED.
- Staging package: uploaded as `ac-staging-package` (artifact ID `15180860714`).
- Pinned open.mp `v1.6.7.3218` headless boot: PASSED.

This run verifies the legal-transition API and staging self-test compilation. It does not execute the test commands with connected game clients.

PR #7 adds live staging commands for interior, virtual-world, and spectating transitions. Its tested head `f56c810ec2344558a959227a646eba99a98751b1` passed GitHub Actions run #57 (`45961527023`):

- Static repository audit: PASSED (35 required files).
- Python unit tests: PASSED (10 tests).
- Deterministic telemetry replay: PASSED (all 10 fixtures).
- Default, opt-in feature-gate, and staging Pawn compiles: PASSED.
- Staging package: uploaded as `ac-staging-package` (artifact ID `15181240532`).
- Pinned open.mp `v1.6.7.3218` headless boot: PASSED.

The headless job does not connect players or issue staging commands. The interior, virtual-world, and spectating commands therefore still require interactive validation with supported game clients. Spectating requires a second connected player. The staging adapter remains RAM-only.

PR #7 was merged to `main` as `da1464dbbe1c499eac074a5a7aa5d8d621b95bc4`. Post-merge GitHub Actions run #59 (`45962033428`) completed successfully:

- Static audit and deterministic Python tests/replay: PASSED.
- Default, opt-in feature-gate, and staging Pawn compiles: PASSED.
- Staging package upload: PASSED (`ac-staging-package`, artifact ID `15180944000`).
- Pinned open.mp `v1.6.7.3218` headless boot: PASSED.

The headless run still did not connect game clients or execute staging commands.

The next staging increment adds pseudonymous structured events and an offline report checker. A successful report requires the expected teleport, vehicle, interior callback, virtual-world, and spectating sequence with no evidence/review markers in the bounded capture. This tool is intended to make a future real-client test auditable; the synthetic success fixture is only a parser regression test and is not runtime evidence.

PR #8, [Add privacy-safe staging acceptance report](https://github.com/yyouki/anticheat/pull/8), tested head `8d781806751783bc86b7077c09191374442947d3` passed GitHub Actions run #62 (`45963399362`):

- Static repository audit: PASSED (38 required files).
- Python unit tests: PASSED (18 tests).
- Deterministic telemetry replay: PASSED (all existing fixtures).
- Default, opt-in feature-gate, and staging Pawn compiles: PASSED.
- Staging package: uploaded as `ac-staging-package` (artifact ID `15181702026`, SHA-256 `dc7e2ee2f92c19e18c762beef4dede469abad342419bb0bf9ad9bb5c8ee10a40`).
- Pinned open.mp `v1.6.7.3218` headless boot: PASSED.

An earlier run #60 (`45963167850`) failed because two existing source-contract tests expected wording removed during README restructuring. The guide was updated to retain the tested contract statements; run #62 passed. Neither run connects a real client. The synthetic success fixture validates only the parser and is not evidence of runtime correctness.


PR #9, [Harden staging acceptance log validation](https://github.com/yyouki/anticheat/pull/9), was merged as `088cd2da36b84f28eb1e6c4cf78f202151aa7ffd`. Post-merge GitHub Actions run #67 (`45973908533`) completed successfully:

- Static repository audit: PASSED (38 required files).
- Python unit tests: PASSED (23 tests).
- Deterministic telemetry replay: PASSED.
- Default, opt-in feature-gate, and staging Pawn compiles: PASSED.
- Staging package: uploaded as `ac-staging-package`, artifact ID `15185799075`, SHA-256 `ae8e9e5a930cf4e7267bc5af8205764708940b266837fb8d7cca833aac497745`.
- Pinned open.mp `v1.6.7.3218` headless boot: PASSED.

PR #9 strengthens required event fields, negative-value rejection, spectate target-role validation, and abort-reason placement. The post-merge workflow still uses a synthetic log fixture and a headless server boot; it does not execute staging commands with connected clients.

The staging report's JSON mode provides a versioned machine-readable representation of the structured-log check. Its `status` and `passed` fields describe only whether the supplied records satisfy the expected log contract. The report explicitly states that client runtime behavior is unverified, log origin is unauthenticated, and production readiness is false. A successful JSON report is not a runtime acceptance result.


PR #10, [Add explicit JSON staging report contract](https://github.com/yyouki/anticheat/pull/10), was merged as 257b3d8bb371639a5d12725111eb9b77991b27ff. Post-merge GitHub Actions run #69 (45976338084) completed successfully:

- Static repository audit, Python unit tests and deterministic replay: PASSED.
- Default, opt-in feature-gate, and staging Pawn compiles: PASSED.
- Staging package upload: PASSED (ac-staging-package, artifact ID 15186404863, SHA-256 82a1cb95ced58ed251ab17755445537f2769ab3b20e774480074bbce191ed699).
- Pinned open.mp v1.6.7.3218 headless boot: PASSED.

Run #69 does not execute connected game clients. The JSON staging report validates only the structured event-log contract.

The next manual-testing increment adds docs/STAGING_FALSE_POSITIVE_MATRIX.md, a versioned review-record template, and tools/anticheat/staging_review.py. They help record benign actions across client builds and network profiles while keeping raw identifiers out of the review schema. The validator reports record completeness and human evidence-review state only; it does not certify test execution, false-positive rate, independent verification, or production readiness. Interactive runtime testing remains outstanding.

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
