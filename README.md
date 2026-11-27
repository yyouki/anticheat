# open.mp Anti-Cheat Framework

A modular, server-side anti-cheat framework for open.mp gamemodes, written in Pawn.

## Project status

The repository contains a modular Pawn core, host-facing callbacks, an evidence-first review policy, and a Python reference model with synthetic telemetry fixtures. The project is still under development and is **not production-ready**: no staging-server runtime suite, desktop/mobile false-positive corpus, expected-capacity benchmark, or independent adversarial review has been completed.

A successful Pawn smoke compile proves compiler/include compatibility for the smoke gamemode. A successful Python replay proves only that the reference model matches its synthetic fixtures. Neither result proves live detector accuracy or bypass resistance.

## Implemented components

- Modular includes for configuration, state, networking, core lifecycle, evidence, player state, movement, vehicle, combat, integrity, and admin helpers.
- Session-token and account-key guards for asynchronous persistence callbacks.
- Grace-window support for server-authoritative transitions.
- Conservative on-foot movement sampling and driver-only vehicle sampling.
- Privacy-safe, bounded staging vehicle observations with measured inter-sample intervals, a local per-model summary, and optional exact capture-to-review binding; none of these measurements change detector thresholds or authenticate log origin.
- Evidence ring buffer, per-category cooldown, cross-family correlation, score/strike review markers, and decay.
- Optional host callbacks for persistence, evidence, strikes, and administrative resets.
- Synthetic JSON fixtures, a deterministic Python reference replay, unit tests, static audit, and Pawn smoke-compilation CI jobs.

## Safety and enforcement policy

Detectors emit evidence; they do not directly punish players. A strike is an investigation marker, not an automatic punishment. The core must not automatically kick, ban, freeze, rewind, or otherwise sanction a player.

Client-originated synchronization is not treated as authoritative by itself. Server-controlled teleports, spawns, world/interior transitions, vehicle placement, and scripted movement should be reported through the host adapter so expected transitions are not misclassified.

Client memory scans are disabled by default. Combat cadence scoring is disabled by default until representative client traces validate it. Do not enable experimental detectors merely because they compile.

## Integration philosophy

The framework is gamemode-neutral. It must not assume a particular account schema, database engine, command processor, roleplay framework, or hosting provider. The host gamemode owns authentication, authorization, persistence implementation, and admin permissions.

See [docs/INTEGRATION.md](docs/INTEGRATION.md) before connecting host callbacks. In particular, persist `last_strike_at` independently from `strike_decay_at`; they represent different clocks.

## Staging harness

An isolated reference gamemode and temporary in-memory persistence adapter are available under [examples/staging](examples/staging/README.md). The harness demonstrates the public account-load/save callbacks, lifecycle forwarding, legal transition notifications, and evidence inspection without selecting a database or authentication provider.

CI compiles the staging gamemode, publishes an `ac-staging-package` artifact, then starts a pinned open.mp Linux server and verifies that the gamemode loads. This is a headless server-boot check only; it does not simulate a connected game client or prove detector accuracy. Follow the manual player test sequence in [examples/staging/README.md](examples/staging/README.md) for interactive runtime validation.

## Development and release gates

Every production candidate must pass:

1. Repository/API and static audit.
2. Default and opt-in Pawn compilation against the pinned supported compiler and open.mp includes.
3. Deterministic Python fixture replay and unit tests.
4. Runtime testing on a staging open.mp server.
5. False-positive tests across supported desktop and Android clients and variable network conditions.
6. Performance tests at expected player capacity.
7. Independent adversarial review, including gradual and correlated manipulation.
8. A reviewed host adapter and administrator-visible evidence trail.

See [docs/ROADMAP.md](docs/ROADMAP.md), [docs/VALIDATION.md](docs/VALIDATION.md), and [docs/PROJECT_CONTEXT.md](docs/PROJECT_CONTEXT.md).

## License

License selection is pending repository-owner confirmation. Until then, do not assume this repository grants reuse rights.
