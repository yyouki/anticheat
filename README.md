# open.mp Anti-Cheat Framework

A modular, server-side anti-cheat framework for open.mp gamemodes.

## Status

Initial repository bootstrap. The first production target is a portable Pawn core that can be integrated by different gamemodes without depending on a particular account schema, command processor, database plugin, or roleplay framework.

The framework is evidence-first: detectors report observations, the core correlates independent evidence, and administrators make enforcement decisions. No detector automatically kicks, bans, freezes, or rewinds players.

## Planned modules

- Movement and player-state telemetry
- Vehicle telemetry
- Combat event telemetry
- Network-quality context
- Client-integrity capability checks (disabled until client/version profiles are validated)
- Evidence ring buffer and cross-detector correlation
- Suspicion scoring, strike policy, and configurable decay
- Gamemode adapter API for legitimate server-side actions
- Optional persistence and admin investigation adapters
- Isolated experiments for native plugins, ML, packet polling, and pathfinding

## Integration philosophy

The framework must not assume that client-synchronized position, velocity, weapon, or damage callbacks are inherently trustworthy. Server-side state and decisions are authoritative; client-originated synchronization is treated as evidence input that must be corroborated.

All legitimate server-controlled teleports, spawns, world/interior transitions, vehicle placement, scripted movement, and health/armour changes should be reported to the adapter so detectors can suppress expected transitions.

## Development gates

Every production feature must pass:

1. Repository and API audit
2. Pawn compilation against the supported open.mp include/compiler
3. Runtime testing on a staging open.mp server
4. False-positive tests across desktop and mobile clients and variable network conditions
5. Performance tests at expected player capacity
6. Adversarial review, including gradual and correlated manipulation

See `docs/ROADMAP.md` and `docs/VALIDATION.md`.

## License

License selection is pending repository-owner confirmation. Until then, do not assume this repository grants reuse rights.
