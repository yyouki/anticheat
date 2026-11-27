#if defined _AC_CORE_INCLUDED
    #endinput
#endif
#define _AC_CORE_INCLUDED

forward AC_OnPersistenceSave(playerid, accountid, score, strikes, score_decay_at, strike_decay_at);
forward AC_OnAdministrativeReset(adminid, targetid, accountid);
forward AC_OnEvidence(playerid, category, points, ping, const reason[], Float:metric);
forward AC_OnStrike(playerid, accountid, strikes, const reason[]);

stock AC_Init()
{
    if (AC_Initialized)
        return 1;

    AC_Initialized = true;
    SetTimer("AC_InternalTick", 30000, true);
    return 1;
}

stock AC_GetVersion(destination[], size = sizeof(destination))
{
    format(destination, size, "%s", AC_VERSION);
    return 1;
}

stock AC_AdvanceSessionToken(playerid)
{
    if (!AC_IsValidPlayerId(playerid))
        return 0;
    AC_SessionToken[playerid]++;
    if (AC_SessionToken[playerid] <= 0)
        AC_SessionToken[playerid] = 1;
    return AC_SessionToken[playerid];
}

stock AC_GetSessionToken(playerid)
{
    if (!AC_IsValidPlayerId(playerid))
        return 0;
    return AC_SessionToken[playerid];
}

stock AC_OnPlayerConnect(playerid)
{
    if (!AC_IsValidPlayerId(playerid))
        return 0;
    AC_AdvanceSessionToken(playerid);
    AC_ResetPlayer(playerid);
    return 1;
}

stock AC_OnPlayerDisconnect(playerid)
{
    if (!AC_IsValidPlayerId(playerid))
        return 0;
    if (AC_PlayerLoaded[playerid] && AC_Dirty[playerid])
        AC_SavePersistentState(playerid);

    AC_AdvanceSessionToken(playerid);
    AC_ResetPlayer(playerid);
    return 1;
}

// Use when the gamemode has no persistence adapter. Advancing the token also
// invalidates any earlier asynchronous load for this player slot.

stock AC_SetIdentity(playerid, accountid)
{
    if (!AC_IsValidPlayerId(playerid) || !IsPlayerConnected(playerid) || accountid <= 0)
        return 0;

    AC_AdvanceSessionToken(playerid);
    AC_ResetPlayer(playerid);
    AC_AccountKey[playerid] = accountid;
    AC_PlayerLoaded[playerid] = true;
    AC_PlayerEnabled[playerid] = true;
    AC_LastScoreDecayAt[playerid] = gettime();
    AC_LastStrikeDecayAt[playerid] = gettime();
    AC_LastPersistAt[playerid] = gettime();
    return 1;
}

// Begin an asynchronous load. Save the returned token and provide it to
// AC_ApplyPersistentState when the database callback completes.
stock AC_BeginAccountLoad(playerid, accountid)
{
    if (!AC_IsValidPlayerId(playerid) || !IsPlayerConnected(playerid) || accountid <= 0)
        return 0;

    AC_AdvanceSessionToken(playerid);
    AC_ResetPlayer(playerid);
    AC_AccountKey[playerid] = accountid;
    return AC_SessionToken[playerid];
}

stock AC_ApplyPersistentState(playerid, accountid, sessiontoken, score, strikes, score_decay_at, strike_decay_at)
{
    if (!AC_IsValidPlayerId(playerid)
        || !IsPlayerConnected(playerid)
        || sessiontoken != AC_SessionToken[playerid]
        || accountid != AC_AccountKey[playerid])
    {
        return 0;
    }

    if (score < 0) score = 0;
    if (score > 100) score = 100;
    if (strikes < 0) strikes = 0;

    AC_SuspicionScore[playerid] = score;
    AC_StrikeCount[playerid] = strikes;
    AC_LastScoreDecayAt[playerid] = score_decay_at > 0 ? score_decay_at : gettime();
    AC_LastStrikeDecayAt[playerid] = strike_decay_at > 0 ? strike_decay_at : gettime();
    AC_LastPersistAt[playerid] = gettime();
    AC_PlayerLoaded[playerid] = true;
    AC_PlayerEnabled[playerid] = true;
    AC_ApplyDecay(playerid);
    return 1;
}

stock AC_SetEnabled(playerid, bool:enabled)
{
    if (!AC_IsValidPlayerId(playerid) || !IsPlayerConnected(playerid) || !AC_PlayerLoaded[playerid])
        return 0;

    AC_PlayerEnabled[playerid] = enabled;
    AC_ResetSampling(playerid);
    return 1;
}

stock bool:AC_IsMonitored(playerid)
{
    return AC_IsValidPlayerId(playerid)
        && IsPlayerConnected(playerid)
        && AC_PlayerLoaded[playerid]
        && AC_PlayerEnabled[playerid];
}

stock AC_NotifyLegitimateTeleport(playerid, milliseconds = AC_DEFAULT_GRACE_MS)
{
    if (!AC_IsValidPlayerId(playerid) || !IsPlayerConnected(playerid))
        return 0;

    AC_GraceStartedTick[playerid] = GetTickCount();
    AC_GraceDurationMs[playerid] = milliseconds;
    AC_ResetSampling(playerid);
    return 1;
}

stock AC_NotifyLegitimateStateChange(playerid, milliseconds = 2500)
{
    return AC_NotifyLegitimateTeleport(playerid, milliseconds);
}

stock AC_NotifyLegitimateSpawn(playerid)
{
    return AC_NotifyLegitimateTeleport(playerid, AC_DEFAULT_GRACE_MS);
}

stock AC_NotifyLegitimateVehicleChange(playerid)
{
    if (!AC_IsValidPlayerId(playerid) || !IsPlayerConnected(playerid))
        return 0;
    AC_VehicleOverLimitSamples[playerid] = 0;
    AC_LastVehicleId[playerid] = INVALID_VEHICLE_ID;
    return 1;
}

stock AC_NotifyLegitimateHealthChange(playerid)
{
    // Health/armour changes are not scored in the initial production baseline.
    return AC_IsValidPlayerId(playerid) && IsPlayerConnected(playerid);
}

stock bool:AC_IsInGrace(playerid)
{
    if (!AC_IsValidPlayerId(playerid))
        return false;
    if (AC_GraceDurationMs[playerid] <= 0)
        return false;

    // Unsigned tick subtraction remains valid across the GetTickCount rollover.
    if ((GetTickCount() - AC_GraceStartedTick[playerid]) < AC_GraceDurationMs[playerid])
        return true;

    AC_GraceDurationMs[playerid] = 0;
    return false;
}

stock AC_SavePersistentState(playerid)
{
    if (!AC_IsValidPlayerId(playerid))
        return 0;
    if (!AC_PlayerLoaded[playerid] || AC_AccountKey[playerid] <= 0)
        return 0;

    new result = CallLocalFunction("AC_OnPersistenceSave", "dddddd",
        playerid,
        AC_AccountKey[playerid],
        AC_SuspicionScore[playerid],
        AC_StrikeCount[playerid],
        AC_LastScoreDecayAt[playerid],
        AC_LastStrikeDecayAt[playerid]
    );

    // The adapter must return 1 after it has accepted the save request.
    AC_Dirty[playerid] = (result != 1);
    AC_LastPersistAt[playerid] = gettime();
    return result == 1;
}

stock AC_ApplyDecay(playerid)
{
    if (!AC_IsValidPlayerId(playerid))
        return 0;
    new now = gettime();
    new elapsed;
    new periods;

    if (AC_LastScoreDecayAt[playerid] <= 0 || AC_LastScoreDecayAt[playerid] > now)
        AC_LastScoreDecayAt[playerid] = now;

    elapsed = now - AC_LastScoreDecayAt[playerid];
    periods = elapsed / AC_SCORE_DECAY_SECONDS;
    if (periods > 0)
    {
        AC_SuspicionScore[playerid] -= periods;
        if (AC_SuspicionScore[playerid] < 0)
            AC_SuspicionScore[playerid] = 0;

        AC_LastScoreDecayAt[playerid] += periods * AC_SCORE_DECAY_SECONDS;
        AC_Dirty[playerid] = true;
    }

    if (AC_LastStrikeDecayAt[playerid] <= 0 || AC_LastStrikeDecayAt[playerid] > now)
        AC_LastStrikeDecayAt[playerid] = now;

    elapsed = now - AC_LastStrikeDecayAt[playerid];
    periods = elapsed / AC_STRIKE_DECAY_SECONDS;
    if (periods > 0)
    {
        AC_StrikeCount[playerid] -= periods;
        if (AC_StrikeCount[playerid] < 0)
            AC_StrikeCount[playerid] = 0;

        AC_LastStrikeDecayAt[playerid] += periods * AC_STRIKE_DECAY_SECONDS;
        AC_Dirty[playerid] = true;
    }
    return 1;
}

forward AC_InternalTick();
public AC_InternalTick()
{
    new now = gettime();

    for (new playerid; playerid < MAX_PLAYERS; playerid++)
    {
        if (!IsPlayerConnected(playerid) || !AC_PlayerLoaded[playerid])
            continue;

        AC_ApplyDecay(playerid);
        if (AC_Dirty[playerid] && (now - AC_LastPersistAt[playerid]) >= AC_PERSIST_INTERVAL_SECONDS)
            AC_SavePersistentState(playerid);
    }
    return 1;
}
