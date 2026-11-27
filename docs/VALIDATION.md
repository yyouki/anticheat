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


PR #11, [Add privacy-safe staging false-positive review ledger](https://github.com/yyouki/anticheat/pull/11), merged as `17192632aab1e8c63c17b3aaac1ebc6fb67f0752`. Post-merge run #71 (`45977639889`) passed all three jobs: static audit, Python tests/replay and Pawn compile/package/headless open.mp smoke. Artifact `ac-staging-package` ID `15187896874`, SHA-256 `9cfff4b4c34ae292d68d11f0f7bbc94a7a31cdd6a0806e9e37b81fd0ba6dc`.

The follow-up batch summary tool groups individually validated operator records by exact server commit, artifact digest, open.mp version, client platform/build label, and network profile. It reports aggregate and per-scenario counts, rejects invalid/duplicate records, and never estimates a false-positive rate. This remains bookkeeping over operator-authored input, not runtime verification.

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


PR #12, [Add multi-run staging review summaries](https://github.com/yyouki/anticheat/pull/12), merged as `18346071602254afa6177bbf2cf9d86f92b246cb`. Post-merge run #75 (`45982873217`) passed all three jobs: static audit, Pawn compile, and pinned open.mp headless runtime smoke. Artifact `ac-staging-package` ID `15189179026`, size 43,718 bytes, SHA-256 `1a0bd8dc250c2771f2177776406a638918bc4560eec5310fddc2a0117668754a`.

PR #12 adds a bounded multi-run summary for operator-entered review records. Counts remain observations, not rates; they do not establish test execution, authenticate logs, or certify detector quality. No connected game-client test was performed by run #75.


PR #13, [Bind staging reviews to exact capture logs](https://github.com/yyouki/anticheat/pull/13), merged as `aa8b0a9809c36b2c75450309a957ca5d6a40b882`. PR workflow run #77 (`45983957773`) and post-merge `main` run #78 (`45984403784`) passed static audit, Python tests/replay, all three Pawn compile targets, staging artifact upload, and pinned open.mp `v1.6.7.3218` headless boot. The post-merge artifact `ac-staging-package` is ID `15191081168`, size 43,973 bytes, SHA-256 `e8a6bb55e841f2017fd93fda59ddcb72fb3de09db6d61b1f67a0e628f30acb60`.

PR #13 changes the manual review schema to v2 and binds each review record to an exact local capture-file digest. This validates file consistency and the structured event contract only; it does not authenticate who produced the log or verify that a human performed the scenario observations. No connected game-client test ran in run #78.


PR #14, [Add deterministic vehicle telemetry replay coverage](https://github.com/yyouki/anticheat/pull/14), merged to `main` as `650fa4fb4eb1dc29ca54a276b6ec98c57657aa70`. Post-merge Actions run #83 (`45990008906`) completed successfully on that exact merge commit:

- Static audit, Python contract tests and deterministic movement/vehicle replay: PASSED.
- Default, opt-in feature-gate, and staging Pawn compiles: PASSED.
- Staging package upload: PASSED (`ac-staging-package`, artifact ID `15192318954`, size 43,973 bytes, SHA-256 `59c41804269ac3d6a12ec5afd6478aa51751ff8b379d7eb9229ff32a6c7ca7e1`).
- Pinned open.mp `v1.6.7.3218` headless boot: PASSED.

Run #83 did not connect an interactive game client. PR #14 expands only the synthetic Python reference replay; it does not change the Pawn vehicle detector or establish model-aware thresholds.


PR #15, [Add bounded staging vehicle telemetry traces](https://github.com/yyouki/anticheat/pull/15), head `59f13bfff954cda534f6d5d5a15201f8218ded33`, passed workflow run #86 (`45991708681`). All three jobs completed successfully:

- Static repository audit, all 77 Python unit tests, and deterministic telemetry replay: PASSED.
- Default, opt-in feature-gate, and staging Pawn compile targets: PASSED.
- Staging artifact upload: PASSED (`ac-staging-package`, ID `15192894648`, size 45,484 bytes, SHA-256 `dd97f0b151c1b513e7d784984529b9553573c3dbe9a71a44bea8ea5f9742f2db`).
- Pinned open.mp headless runtime smoke: PASSED.

PR #15 adds observational vehicle traces and a local per-model summary only. It does not modify Pawn detector thresholds or establish a safe speed envelope. Run #86 did not connect interactive game clients or collect real vehicle traces.


PR #15, [Add bounded staging vehicle telemetry traces](https://github.com/yyouki/anticheat/pull/15), merged to `main` as `3437bca25682efb01c0bed559d510d9853c65074`. Post-merge run #90 (`45996487757`) completed successfully on that exact merge commit:

- Static repository audit, Python tests, and deterministic telemetry replay: PASSED.
- Default, opt-in feature-gate, and staging Pawn compiles: PASSED.
- Staging package upload: PASSED (`ac-staging-package`, ID `15195404151`, size 45,484 bytes, SHA-256 `26edf768a6d41783ba20a977fc3161aa04a5787d6a7df98aa30ba35ad2770ea2`).
- Pinned open.mp `v1.6.7.3218` headless boot: PASSED.

Run #90 did not connect an interactive game client or collect real vehicle traces. The detector thresholds remain unchanged.


PR #16, [Bind vehicle trace summaries to staging review captures](https://github.com/yyouki/anticheat/pull/16), head `dbd8dfc5bcad2ca18dff77cfc97845e24c794055`, passed workflow run #92 (`45997360443`). All three jobs completed successfully:

- Static repository audit, all 90 Python unit tests, and deterministic telemetry replay: PASSED.
- Default, opt-in feature-gate, and staging Pawn compile targets: PASSED.
- Staging artifact upload: PASSED (`ac-staging-package`, ID `15195659656`, size 45,753 bytes, SHA-256 `0669d424bb0f50aa9ed34e39ad8472a7c3f6dcd1eb5eefd5972f42ad9ca575f2`).
- Pinned open.mp `v1.6.7.3218` headless runtime smoke: PASSED.

PR #16 adds local capture-to-review consistency validation only. Bound reports verify exact file digests and matching operator-entered metadata, but do not authenticate log origin or prove that a human executed the scenarios. No interactive client tests or detector-threshold changes were made.
