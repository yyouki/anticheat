# Roadmap

## Milestone 0 — standalone Pawn core

- [x] Establish independent repository and public module layout.
- [x] Avoid Pylance Roleplay symbols and database assumptions.
- [x] Implement lifecycle, identity/session token, grace-window and persistence callbacks.
- [x] Implement evidence ring, category correlation, score/strike policy and decay.
- [x] Implement conservative movement and driver-only vehicle sampling.
- [x] Keep memory scans and combat cadence scoring disabled by default.
- [x] Validate default and compile-only opt-in feature-gate builds with the pinned CI compiler and open.mp includes.
- [x] Add defensive player-ID validation to per-player state, lifecycle, network and evidence helpers.
- [x] Reject duplicate asynchronous account-load completions after the active session has already been loaded.
- [x] Restore an active strike cooldown from the persisted `last_strike_at` timestamp; keep it separate from the six-hour `strike_decay_at` timestamp.
- [x] Add a neutral staging gamemode with a volatile persistence adapter and legal transition test commands.
- [x] Compile and package the staging AMX in CI; run a headless boot check against a pinned open.mp server release.
- [ ] Complete interactive staging tests with supported game clients, including false-positive review.
- [ ] Complete staging-server runtime and false-positive testing.

## Milestone 1 — investigation and host adapters

- [x] Provide framework-neutral admin status/evidence/reset helpers.
- [x] Provide evidence, strike, persistence and administrative-reset callbacks.
- [ ] Add tested adapters for common command processors as optional packages.
- [ ] Add an optional durable evidence storage adapter with retention controls.
- [x] Add versioned synthetic telemetry fixtures and a deterministic Python reference replay.
- [x] Add CI regression tests for movement grace, sustained anomalies, network suppressors, sampling resets, evidence correlation, and stale/duplicate account loads.
- [x] Repair replay/unit-test CI regression in PR #3; post-merge main run #37 passed all automated checks.

## Milestone 2 — detection coverage

- [ ] Add model-aware vehicle envelopes from staging traces.
- [ ] Add server action provenance helpers for all common legal transitions.
- [ ] Add combat heuristics only after mobile/desktop false-positive evidence.
- [ ] Add network packet-loss context only through a validated low-cost source.
- [ ] Add explicit player-state anomaly evidence after defining legal state transitions.

## Milestone 3 — experiments (non-production)

- [ ] C/C++ native profiling experiment.
- [ ] Rust sidecar/FFI feasibility experiment.
- [ ] ML evaluation using labelled, anonymised and representative traces.
- [ ] Path plausibility/pathfinding evaluation with bounded compute.
- [ ] Version-specific client integrity profiles.

Experiments cannot be promoted based solely on a successful compile. They must satisfy the release gates in docs/VALIDATION.md.
