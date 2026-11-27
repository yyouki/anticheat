# Architecture

## Trust boundary

The server owns authentication state, detector configuration, scoring, evidence correlation, strike policy, persistence decisions, and administrator review. open.mp still receives client-originated synchronization for position, velocity, weapon, and damage-related callbacks. These values are therefore observations, not unquestionable proof.

The framework is not a client-side anti-tamper product. It must not describe client memory checks, official-client identification, or client-reported values as a reliable verdict.

## Production module map

| File | Responsibility |
| --- | --- |
| include/ac/config.inc | Conservative thresholds and feature gates |
| include/ac/state.inc | Per-player session, score, evidence and sampling state |
| include/ac/network.inc | Ping and optional host-supplied packet-loss context |
| include/ac/core.inc | Lifecycle, identity, grace windows, decay and persistence adapter |
| include/ac/evidence.inc | Evidence ring buffer, scoring and cross-category correlation |
| include/ac/player_state.inc | Spawn, death and state-transition helpers |
| include/ac/movement.inc | Rate-limited on-foot position sampling |
| include/ac/vehicle.inc | Driver-only vehicle velocity envelope |
| include/ac/combat.inc | Disabled-by-default damage cadence experiment |
| include/ac/integrity.inc | Client-check capability boundary; no memory scan enabled |
| include/ac/admin.inc | Framework-neutral status, evidence and reset helpers |
| include/ac.inc | Public umbrella include |

## Lifecycle

1. The host calls AC_Init once during OnGameModeInit.
2. The host calls AC_OnPlayerConnect and AC_OnPlayerDisconnect from the matching callbacks.
3. After successful authentication, the host calls AC_SetIdentity, or starts an asynchronous load through AC_BeginAccountLoad and completes it with AC_ApplyPersistentState.
4. The host forwards OnPlayerUpdate, OnPlayerSpawn, OnPlayerDeath, OnPlayerStateChange, OnPlayerGiveDamage, OnPlayerWeaponShot and OnClientCheckResponse to the corresponding AC_ functions.
5. Before a legitimate server-side position/state/vehicle transition, the host calls the matching AC_NotifyLegitimate... helper. Explicit wrappers cover teleports, interior changes, virtual-world changes, spectating changes, spawn, and vehicle transitions; other scripted state changes use AC_NotifyLegitimateStateChange.
6. Optional callbacks receive evidence, strikes, administrative resets and persistence requests.

The library does not replace existing callbacks. The gamemode must forward to the framework from its existing callback bodies or use its established callback-hook mechanism. Do not define duplicate callbacks.

## Staging integration harness

`examples/staging.pwn` is a disposable open.mp gamemode for validating host integration. It forwards the normal lifecycle/update callbacks and uses the same public persistence callback signatures as a real host.

Its adapter stores synthetic account state in bounded process memory and preserves the three independent timestamps. It is deliberately volatile and is not a production database implementation. The sample provides commands for authentication simulation, save/restore, state inspection, review-state clearing, and server-owned legal teleport/vehicle transitions.

CI compiles this gamemode, packages the AMX, and boots it on a pinned open.mp Linux server. The boot probe confirms only that the server and gamemode load; player synchronization, false-positive behavior, persistence across a server restart, and live performance remain manual staging gates.

## Detector policy

### Movement
On-foot positions are sampled no more often than twice per second. The first sample establishes a baseline. Interior/world/state transitions, spawn, death, spectating changes, grace windows, high ping, high supplied packet loss, and long sample gaps reset or suppress sampling. Server-owned interior, virtual-world, and spectating operations should be preceded by their explicit notification helper. A speed anomaly must persist across multiple valid samples before evidence is recorded. The initial detector uses XY distance; it does not infer a teleport solely from a single position update.

### Vehicle
Only the server-reported driver is sampled. open.mp vehicle velocity is converted with the documented 250.66667 km/h factor. Aircraft, boats, trains, and other special vehicle classes are excluded from this generic speed envelope. Per-model handling and collision impulses need staging traces before more precise thresholds can be enabled.

### Combat
Shot and damage callbacks can be incomplete or inaccurate. Combat cadence scoring is compile-time disabled by default. The optional generic damage-cadence detector must remain advisory until it passes mobile, weapon, lag compensation, multi-target, and high-ping false-positive tests. Aim-bot and hitbox inference are not part of v1.

### Player state
State changes are context and grace events, not evidence by themselves. The framework does not score passenger transitions, death, spawn, spectating, or interior changes as cheating.

### Network
The default network signal is GetPlayerPing. An optional host adapter may call AC_SetNetworkQuality with a validated packet-loss measurement. Severe network degradation suppresses scoring; it never increases suspicion. The framework does not add per-player packet polling.

### Client integrity
AC_ENABLE_CLIENT_MEMORY_CHECKS is disabled. No generic SendClientCheck address/offset scan is performed. Version-specific profiles require separate review for each supported desktop/mobile client version and must never treat an absent response as proof of cheating.

## Evidence and scoring

- Evidence is stored in a small per-player ring buffer.
- Each detector family has a cooldown.
- Evidence from distinct categories in a 120-second window can receive a small correlation bonus.
- Suspicion is clamped to 0..100.
- A strike requires a high score, at least one other recently active detector family, and a strike cooldown.
- Suspicion decays by one point every five minutes.
- Strikes decay by one every six hours, beginning from the most recent strike.
- The core does not store a database schema. The host receives AC_OnPersistenceSave and decides how to store account-keyed state, including the distinct strike-decay and last-strike timestamps needed to restore cooldown semantics after reconnect.
- Evidence details are session-local in v1. Hosts needing durable forensic history should implement AC_OnEvidence persistence with retention and privacy controls.

## Admin tooling

AC_AdminStatus, AC_AdminEvidence, and AC_AdminClear are helper functions, not commands. They deliberately do not authorize administrators. The host gamemode must perform permission checks before calling them and should implement AC_OnAdministrativeReset for an audit trail.

## Native and ML policy

Pawn is the production implementation because the framework is integrated into Pawn callbacks and has no demonstrated CPU bottleneck. C/C++/Rust, hybrid inference, ML, packet polling and pathfinding remain isolated experiments. No native extension is promoted without profiling, cross-platform builds, fuzzing, bounded runtime, parity tests, and rollback.
