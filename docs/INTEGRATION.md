# Gamemode integration

## Include and initialization

Add the repository's include directory to the Pawn compiler include path, then include ac.inc from the gamemode:

    #include <ac>

Call AC_Init once from the existing OnGameModeInit callback.

## Forward existing callbacks

Do not create duplicate public callbacks. Add the AC_ calls inside the gamemode's existing callback implementations:

    AC_OnPlayerConnect(playerid);
    AC_OnPlayerDisconnect(playerid);
    AC_OnPlayerSpawn(playerid);
    AC_OnPlayerDeath(playerid);
    AC_OnPlayerStateChange(playerid, newstate, oldstate);
    AC_OnPlayerUpdate(playerid);
    AC_OnPlayerGiveDamage(playerid, damagedid, amount);
    AC_OnPlayerWeaponShot(playerid, weaponid, hittype, hitid);
    AC_OnClientCheckResponse(playerid, actionid, memaddr, retndata);

The smoke gamemode in examples/smoke.pwn shows the callback signatures. Preserve the gamemode's existing callback return behavior.

## Authentication and persistence

Do not enable detection while the player is still connecting, logging in, selecting a character, or waiting for asynchronous data.

For a host without persistence, call AC_SetIdentity(playerid, accountid) only after the character is ready.

For asynchronous persistence:

1. Call AC_BeginAccountLoad(playerid, accountid) and save the returned session token with the pending query.
2. When the account query completes, call AC_ApplyPersistentState(playerid, accountid, sessiontoken, score, strikes, score_decay_at, strike_decay_at, last_strike_at).
3. The token and account key prevent a late query callback from activating a reused player slot or a different account. Only the first matching completion is accepted; duplicate completions for an already-loaded session are rejected.
4. Persist and restore the timestamps independently:
   - `score_decay_at` drives the score decay schedule.
   - `strike_decay_at` drives the six-hour strike decay schedule.
   - `last_strike_at` records when the most recent strike occurred and restores an active five-minute strike cooldown after reconnect.

Implement public AC_OnPersistenceSave(playerid, accountid, score, strikes, score_decay_at, strike_decay_at, last_strike_at). Return 1 only when the save request has been accepted by the host persistence layer.

The host adapter must save and pass all three timestamps through AC_OnPersistenceSave and AC_ApplyPersistentState. Do not substitute `strike_decay_at` for `last_strike_at`: doing so can restart an expired five-minute cooldown when the six-hour decay timestamp is updated.

No MySQL plugin, SQLite library, ORM, database engine, or table schema is required by the core.

## Legitimate action notifications

Notify the framework immediately before a server-controlled operation that changes a player's position or movement context:

- Call `AC_NotifyLegitimateTeleport(playerid)` before `SetPlayerPos` or `SetPlayerPosEx`.
- Call `AC_NotifyLegitimateInteriorChange(playerid)` before `SetPlayerInterior`.
- Call `AC_NotifyLegitimateVirtualWorldChange(playerid)` before `SetPlayerVirtualWorld`.
- Call `AC_NotifyLegitimateSpectateChange(playerid)` before `TogglePlayerSpectating`, `PlayerSpectatePlayer`, or `PlayerSpectateVehicle`.
- Call `AC_NotifyLegitimateSpawn(playerid)` for a server-controlled spawn. The forwarded `OnPlayerSpawn` handler already does this.
- Call `AC_NotifyLegitimateStateChange(playerid, milliseconds)` for another scripted state transition that changes movement context but does not fit the named helpers.

The interior, virtual-world, and spectating helpers accept an optional grace duration in milliseconds and default to `AC_DEFAULT_GRACE_MS`. Each validates the player and resets movement sampling through the shared state-change path.

Call `AC_NotifyLegitimateVehicleChange(playerid)` when server logic places a player in a vehicle, removes them, or otherwise changes their vehicle. `AC_NotifyLegitimateHealthChange` is currently a no-op compatibility hook; health/armour are not scored in v1.

Place the notification before the server action, not after it. Do not add grace markers to arbitrary client movement. Only server-controlled legal actions should be acknowledged.

## Network adapter

The framework uses GetPlayerPing by default. If the gamemode already has a trustworthy, low-cost packet-loss measurement, it may call AC_SetNetworkQuality(playerid, ping, packet_loss) when that measurement is refreshed. The value expires after three seconds. Do not add a new tight polling loop just for this adapter.

## Admin helpers

Before calling AC_AdminStatus, AC_AdminEvidence, or AC_AdminClear, enforce the host gamemode's admin permission and target validity. Implement AC_OnAdministrativeReset if the reset must be written to the existing admin audit log.

## Reference staging gamemode

Use [examples/staging/README.md](../examples/staging/README.md) and `examples/staging.pwn` as a working integration reference. The sample uses a temporary in-memory persistence adapter so the callback contract can be tested without imposing a database engine or schema. Its stored records are lost on server restart; do not reuse it as a production persistence layer.

## Evidence callbacks

Optional public callbacks:

- AC_OnEvidence: a detector has emitted one evidence record.
- AC_OnStrike: correlated evidence crossed the review threshold.
- AC_OnPersistenceSave: the core asks the host to save account-keyed score/strike state.
- AC_OnAdministrativeReset: an administrator cleared review state.

A strike is an investigation marker, not an automatic punishment.
