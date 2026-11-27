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
2. When the account query completes, call AC_ApplyPersistentState(playerid, accountid, sessiontoken, score, strikes, score_decay_at, strike_decay_at).
3. The token and account key prevent a late query callback from activating a reused player slot or a different account. Only the first matching completion is accepted; duplicate completions for an already-loaded session are rejected.
4. Keep the supplied strike-decay timestamp with the account state. During an active five-minute strike cooldown it also lets the core restore the cooldown after reconnect; the same timestamp still drives the six-hour strike decay.
4. Implement public AC_OnPersistenceSave(playerid, accountid, score, strikes, score_decay_at, strike_decay_at). Return 1 only when the save request has been accepted by the host persistence layer.

No MySQL plugin, SQLite library, ORM, or table schema is required by the core.

## Legitimate action notifications

Call AC_NotifyLegitimateTeleport before server-authoritative SetPlayerPos/SetPlayerPosEx operations. Also notify the framework about scripted spawn, interior/world transitions and state transitions when appropriate.

Call AC_NotifyLegitimateVehicleChange when server logic places a player in a vehicle or changes their vehicle. AC_NotifyLegitimateHealthChange is currently a no-op compatibility hook; health/armour are not scored in v1.

Do not add grace markers to arbitrary client movement. Only server-controlled legal actions should be acknowledged.

## Network adapter

The framework uses GetPlayerPing by default. If the gamemode already has a trustworthy, low-cost packet-loss measurement, it may call AC_SetNetworkQuality(playerid, ping, packet_loss) when that measurement is refreshed. The value expires after three seconds. Do not add a new tight polling loop just for this adapter.

## Admin helpers

Before calling AC_AdminStatus, AC_AdminEvidence, or AC_AdminClear, enforce the host gamemode's admin permission and target validity. Implement AC_OnAdministrativeReset if the reset must be written to the existing admin audit log.

## Evidence callbacks

Optional public callbacks:

- AC_OnEvidence: a detector has emitted one evidence record.
- AC_OnStrike: correlated evidence crossed the review threshold.
- AC_OnPersistenceSave: the core asks the host to save account-keyed score/strike state.
- AC_OnAdministrativeReset: an administrator cleared review state.

A strike is an investigation marker, not an automatic punishment.
