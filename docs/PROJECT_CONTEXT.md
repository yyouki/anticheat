# Project Context and Handoff

This document is the durable handoff for maintainers and coding agents. Read it before making architectural changes. Keep it updated when repository state, interfaces, validation evidence, or project direction changes.

## Project identity

- Repository: `yyouki/anticheat`
- Product: modular, server-side anti-cheat framework for open.mp gamemodes.
- Primary implementation language: Pawn.
- Supporting tooling: Python 3 reference telemetry replay and unit tests.
- Current API/version marker: `AC_VERSION 0.1.0`.
- Default branch: `main`.
- Project maturity: experimental and not production-ready.

This repository is independent of Pylance Roleplay. Do not couple the framework to Pylance-specific symbols, account tables, database migrations, faction/job systems, or a particular roleplay gamemode.

## Non-negotiable design constraints

1. **Evidence-first:** detectors emit explainable evidence. Evidence and strikes are review signals, not automatic punishments.
2. **No automatic enforcement:** do not introduce automatic kick, ban, freeze, rewind, or other punishment in the core.
3. **Server authority:** client-originated synchronization is untrusted input; host-owned server actions should be explicitly reported through adapter hooks.
4. **Gamemode neutrality:** do not assume an account schema, database engine, command processor, hosting provider, or authentication flow.
5. **Conservative detection:** suppress or reset uncertain samples instead of treating poor network quality or legal scripted transitions as suspicious.
6. **Experimental gates:** memory scans and combat cadence scoring stay disabled by default until representative client/runtime evidence exists.
7. **Runtime honesty:** static audit, compilation, and Python replay are separate validation layers. None substitutes for an open.mp staging server, desktop/mobile false-positive tests, performance measurements, or adversarial review.
8. **Privacy:** fixtures must use synthetic account IDs, relative coordinates, and monotonic timestamps. Never commit account names, IP addresses, session secrets, real player identifiers, or private chat.

## Current architecture

The public include surface is `include/ac.inc`. The modular implementation is under `include/ac/`:

| Area | Responsibility |
| --- | --- |
| `config.inc` | Core limits, score/strike thresholds, sampling values, feature gates. |
| `state.inc` | Per-player state storage. |
| `network.inc` | Ping and optional packet-loss freshness/reliability context. |
| `core.inc` | Initialization, lifecycle/session state, persistence callbacks and decay. |
| `evidence.inc` | Evidence buffer, category cooldown, cross-family correlation and review strikes. |
| `player_state.inc` | Player lifecycle/state helpers. |
| `movement.inc` | Conservative on-foot movement sampling. |
| `vehicle.inc` | Driver-only vehicle telemetry sampling. |
| `combat.inc` | Experimental combat path; disabled by default. |
| `integrity.inc` | Client-integrity hooks; memory scans disabled by default. |
| `admin.inc` | Framework-neutral status/evidence/reset helpers. |

Supporting validation lives in:

- `tools/anticheat/replay.py`: Python reference model and fixture runner.
- `tools/anticheat/openmp_runtime_smoke.py`: starts the pinned open.mp server and verifies that the staging gamemode loads.
- `tools/anticheat/staging_report.py`: validates one privacy-safe interactive staging capture.
- `tests/test_replay.py` and `tests/test_staging_report.py`: tests for replay outcomes, telemetry contracts, staging-report parsing, and source invariants.
- `tests/fixtures/`: synthetic JSON telemetry scenarios and a pseudonymous staging acceptance log.
- `.github/workflows/`: static audit, Python tests/replays and Pawn smoke builds.
- `docs/INTEGRATION.md`: host gamemode callback and persistence contract.
- `docs/TELEMETRY_REPLAY.md`: fixture schema, semantics and local commands.
- `docs/VALIDATION.md`: current validation evidence and release gates.
- `docs/ROADMAP.md`: milestone tracking.
- `examples/staging.pwn` and `examples/staging/`: isolated staging gamemode, private config, and manual player-test instructions. The adapter is volatile RAM only.

## Persistence contract: keep timestamps distinct

The host adapter is responsible for durable storage. The core does not require or impose a database schema or migration.

The host must pass the three time fields through both `AC_ApplyPersistentState` and `AC_OnPersistenceSave`:

- `score_decay_at`: score decay schedule.
- `strike_decay_at`: six-hour strike decay schedule.
- `last_strike_at`: actual time of the latest strike; used to restore an unexpired five-minute strike cooldown after reconnect.

Do not reuse `strike_decay_at` as `last_strike_at`. They are different clocks. The additional `last_strike_at` parameter is an adapter compatibility requirement introduced in PR #2.

The callback API currently uses:
```pawn
AC_ApplyPersistentState(playerid, accountid, sessiontoken, score, strikes,
    score_decay_at, strike_decay_at, last_strike_at);

public AC_OnPersistenceSave(playerid, accountid, score, strikes,
    score_decay_at, strike_decay_at, last_strike_at);
```

Always use a session token and account key to reject stale asynchronous loads and reused player slots. Only one matching load completion should activate a session.

## Merged history and verified CI

- PR #1, modular Pawn bootstrap, merged to `main`.
  - Merge commit: `9ad5af6bf5c4ad33f24b207dbab9042eb6f03380`.
- PR #2, deterministic telemetry replay suite, merged to `main`.
  - Merge commit: `c288eec29042b509156fa0e48b481098074403cc`.
  - Its original Python CI failed because the replay loader searched in the wrong include file.
- PR #3, replay CI repair and durable project context, merged to `main`.
  - PR: https://github.com/yyouki/anticheat/pull/3
  - Merge commit: `5bf1443a87ec132ba6d93655b45f4b89427fa2e8`.
  - Post-merge Actions run #37 (`45946672307`) passed static audit, Python tests, all 10 replay fixtures, default Pawn smoke compile, and opt-in feature-gate compile.
- PR #4, open.mp staging integration harness, merged to `main`.
  - PR: https://github.com/yyouki/anticheat/pull/4
  - Merge commit: `c0591531c02dc7829e5b0964081f8d177c2d100b`.
  - Post-merge Actions run #46 (`45951716621`) passed audit, Python tests/replay, all three Pawn compile targets, artifact upload, and headless open.mp boot.
- PR #5, staging persistence and session self-tests, merged to `main`.
  - PR: https://github.com/yyouki/anticheat/pull/5
  - Merge commit: `60a9b4d080034be41613959c369c8af1fcdef8d0`.
  - PR head run #51 (`45955418806`) and post-merge run #52 (`45956905920`) passed all jobs.
  - Post-merge staging artifact: `ac-staging-package`, ID `15178982257`.
- PR #6, explicit legal transition notification hooks, merged to `main`.
  - PR: https://github.com/yyouki/anticheat/pull/6
  - Merge commit: `003793945a546c8eb25b67c8036ad19cf633301e`.
  - PR head run #55 (`45957683000`) and post-merge run #56 (`45959927009`) passed all jobs.
  - Post-merge staging artifact: `ac-staging-package`, ID `15180860714`.
- PR #7, live staging commands for legal state transitions, merged to `main`.
  - PR: https://github.com/yyouki/anticheat/pull/7
  - Merge commit: `da1464dbbe1c499eac074a5a7aa5d8d621b95bc4`.
  - Post-merge run #59 (`45962033428`) passed static audit, all Python tests/replay, all three Pawn compile targets, staging artifact upload, and pinned open.mp headless boot.
  - Artifact: `ac-staging-package`, ID `15180944000`, SHA-256 `1914e4b4d0387ef7224a868d52dde8f20050e59f1943351c6093b013c130bc2d`.
- PR #8, privacy-safe staging acceptance report, merged to `main`.
  - PR: https://github.com/yyouki/anticheat/pull/8
  - Merge commit: `49c7b4476d136b7f8117118644915d63485fc9cf`.
  - Post-merge run #65 (`45965726373`) passed.
- PR #9, strict staging acceptance log validation, merged to `main`.
  - PR: https://github.com/yyouki/anticheat/pull/9
  - Merge commit: `088cd2da36b84f28eb1e6c4cf78f202151aa7ffd`.
  - Post-merge run #67 (`45973908533`) passed static audit (38 files), 23 Python unit tests, replay, all three Pawn compile targets, staging package upload, and pinned open.mp headless boot.
  - Artifact: `ac-staging-package`, ID `15185799075`, SHA-256 `ae8e9e5a930cf4e7267bc5af8205764708940b266837fb8d7cca833aac497745`.
- PR #10, versioned JSON staging report output, merged to `main`.
  - PR: https://github.com/yyouki/anticheat/pull/10
  - Merge commit: `257b3d8bb371639a5d12725111eb9b77991b27ff`.
  - Post-merge run #69 (`45976338084`) passed all three jobs.
  - Artifact: `ac-staging-package`, ID `15186404863`, SHA-256 `82a1cb95ced58ed251ab17755445537f2769ab3b20e774480074bbce191ed699`.

A PR being merged does not imply every CI job passed. Always verify the latest workflow for the resulting `main` commit.

## Working and merge workflow preference

The repository owner prefers a low-friction merge process and does not want routine manual line-by-line PR review as a required step.

- Before proposing a merge, perform the code/diff inspection and run the full relevant CI suite yourself.
- When CI is green and no unresolved blocker is known, provide a concise summary, test results, and remaining limitations. Do not ask the owner to repeat a manual review just to proceed.
- Keep PR descriptions clear and mark the PR ready when its checks pass.
- Do not merge on the owner's behalf unless the owner explicitly asks you to do so.
- If CI fails, a security-sensitive change is involved, or the diff contains an unresolved risk, explain that specific blocker instead of treating manual review as a generic checklist.

## Local validation commands

From the repository root:

```sh
python3 -m unittest discover -s tests -v
python3 tools/anticheat/replay.py
```

CI also performs the repository static audit and default/opt-in Pawn smoke compilation with the pinned compiler and open.mp standard include revision. Confirm the workflow YAML for the exact pinned versions; do not silently update toolchain pins as part of an unrelated task.

## Work sequence and project rules

1. Read this file, `README.md`, `docs/ROADMAP.md`, `docs/VALIDATION.md`, and the relevant implementation/tests before editing.
2. Work on a dedicated branch based on the latest `main`, unless a small documentation-only correction is clearly safer directly on `main`.
3. Keep changes scoped, preserve public callback signatures unless compatibility impact is explicitly documented, and update tests/docs with behavior changes.
4. Run focused tests, then the full CI workflow. Inspect failed logs instead of guessing.
5. Never change fixture expectations merely to silence a regression.
6. Do not mark a feature production-ready because it compiles or passes synthetic replay.
7. Update this document whenever merged PRs, public API contracts, known CI state, release gates, or project preferences change.

## Current staging work and verified CI

PR #7, [Add live staging commands for legal state transitions](https://github.com/yyouki/anticheat/pull/7), is merged as `da1464dbbe1c499eac074a5a7aa5d8d621b95bc4`. Its post-merge run #59 passed all three jobs.

PR #8, [Add privacy-safe staging acceptance report](https://github.com/yyouki/anticheat/pull/8), is merged as `49c7b4476d136b7f8117118644915d63485fc9cf`. Post-merge run #65 (`45965726373`) passed.

PR #9, [Harden staging acceptance log validation](https://github.com/yyouki/anticheat/pull/9), is merged as `088cd2da36b84f28eb1e6c4cf78f202151aa7ffd`. Post-merge run #67 (`45973908533`) passed static audit (38 files), 23 Python unit tests, replay, all three Pawn compile targets, staging package upload, and pinned open.mp `v1.6.7.3218` headless boot.

PR #10, [Add explicit JSON staging report contract](https://github.com/yyouki/anticheat/pull/10), is merged as `257b3d8bb371639a5d12725111eb9b77991b27ff`. Post-merge run #69 (`45976338084`) passed all three jobs and uploaded artifact `ac-staging-package` ID `15186404863`, SHA-256 `82a1cb95ced58ed251ab17755445537f2769ab3b20e774480074bbce191ed699`.

The staging capture uses pseudonymous `[AC-STAGE-EVENT]` records and `/acstagelogbegin` / `/acstagelogend`. The offline parser validates one bounded transition capture and its versioned JSON mode reports only structured-log contract results. It does not authenticate log origin or prove client runtime behavior.

The sample adapter remains volatile RAM only. The staging report's synthetic success fixture is parser coverage, not runtime evidence.

## Current manual false-positive evaluation tools

- `docs/STAGING_FALSE_POSITIVE_MATRIX.md` defines benign scenarios across client builds and controlled network profiles.
- `tools/anticheat/staging_review_scenarios.json` is the versioned scenario manifest.
- `docs/templates/staging-review-template.json` is a local-only template; it intentionally starts with unfilled environment metadata and all scenarios marked `not_run`.
- `tools/anticheat/staging_review.py` validates one operator-authored JSON review record and reports missing, blocked, not-run, pending, inconclusive, and confirmed false-positive outcomes.
- The review validator never certifies that tests were actually executed, that the detector is false-positive-free, or that the project is production-ready.

## Remaining release gates

1. Run `/acstagetest` and one complete `/acstagelogbegin`–`/acstagelogend` capture on an isolated private open.mp server with two connected test clients; inspect the offline report.
2. Perform the benign scenario matrix separately for supported desktop and Android client builds and each relevant network profile. Use real disconnect/reconnect testing; the simulated `/acstagetest` reset is not a substitute.
3. Review every evidence event, record its human adjudication, and resolve confirmed false positives before considering threshold changes.
4. Benchmark runtime cost and review adversarial traces before changing detector thresholds.
5. Replace the sample RAM adapter only in a host-specific integration package with a known persistence contract.
