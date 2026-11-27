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
- `tests/test_replay.py`: unit tests for replay outcomes, schema/order checks and selected source contracts.
- `tests/fixtures/`: version-1 synthetic JSON telemetry scenarios.
- `.github/workflows/`: static audit, Python tests/replays and Pawn smoke builds.
- `docs/INTEGRATION.md`: host gamemode callback and persistence contract.
- `docs/TELEMETRY_REPLAY.md`: fixture schema, semantics and local commands.
- `docs/VALIDATION.md`: current validation evidence and release gates.
- `docs/ROADMAP.md`: milestone tracking.

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
  - PR head: `18b2c211257318e90377d807b2e5a60fb0c22f9b`.
  - PR Actions run #36 (`45945528117`) passed all checks.
  - Post-merge `main` Actions run #37 (`45946672307`) also passed: static audit, 5 Python unit tests, all 10 replay fixtures, default Pawn smoke compile, and opt-in feature-gate compile.

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

## Next work

1. Design staging-server integration with a neutral sample gamemode and a minimal persistence adapter.
2. Collect representative desktop/mobile traces and legal-transition cases before tightening movement/vehicle/combat thresholds.
3. Add only host-neutral optional adapters after their public API and failure behavior are tested.
