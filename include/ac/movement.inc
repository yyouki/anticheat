#if defined _AC_MOVEMENT_INCLUDED
    #endinput
#endif
#define _AC_MOVEMENT_INCLUDED

stock AC_UpdateMovementBaseline(playerid, Float:x, Float:y, PLAYER_STATE:player_state, tick)
{
    AC_LastMovementX[playerid] = x;
    AC_LastMovementY[playerid] = y;
    AC_LastMovementTick[playerid] = tick;
    AC_LastMovementInterior[playerid] = GetPlayerInterior(playerid);
    AC_LastMovementWorld[playerid] = GetPlayerVirtualWorld(playerid);
    AC_LastMovementState[playerid] = _:player_state;
    AC_HasMovementSample[playerid] = true;
    AC_MovementOverLimitSamples[playerid] = 0;
    return 1;
}

stock AC_OnPlayerUpdate(playerid)
{
    if (!AC_IsMonitored(playerid))
        return 0;

    new tick = GetTickCount();
    if ((tick - AC_LastUpdateTick[playerid]) < AC_SAMPLE_INTERVAL_MS)
        return 0;
    AC_LastUpdateTick[playerid] = tick;

    if (!AC_IsNetworkSampleReliable(playerid, AC_MOVEMENT_MAX_PING))
    {
        AC_HasMovementSample[playerid] = false;
        AC_MovementOverLimitSamples[playerid] = 0;
        AC_VehicleOverLimitSamples[playerid] = 0;
        return 0;
    }

    new PLAYER_STATE:player_state = GetPlayerState(playerid);
    if (player_state == PLAYER_STATE_DRIVER)
    {
        AC_HasMovementSample[playerid] = false;
        AC_OnVehicleSample(playerid);
        return 1;
    }

    AC_VehicleOverLimitSamples[playerid] = 0;
    AC_LastVehicleId[playerid] = INVALID_VEHICLE_ID;

    if (player_state != PLAYER_STATE_ONFOOT)
    {
        AC_HasMovementSample[playerid] = false;
        AC_MovementOverLimitSamples[playerid] = 0;
        return 0;
    }

    new Float:x, Float:y, Float:z;
    if (!GetPlayerPos(playerid, x, y, z))
        return 0;
    #pragma unused z

    if (AC_IsInGrace(playerid))
    {
        AC_UpdateMovementBaseline(playerid, x, y, player_state, tick);
        return 1;
    }

    if (!AC_HasMovementSample[playerid]
        || AC_LastMovementInterior[playerid] != GetPlayerInterior(playerid)
        || AC_LastMovementWorld[playerid] != GetPlayerVirtualWorld(playerid)
        || AC_LastMovementState[playerid] != _:player_state)
    {
        AC_UpdateMovementBaseline(playerid, x, y, player_state, tick);
        return 1;
    }

    new elapsed = tick - AC_LastMovementTick[playerid];
    if (elapsed < 250 || elapsed > AC_MAX_SAMPLE_GAP_MS)
    {
        AC_UpdateMovementBaseline(playerid, x, y, player_state, tick);
        return 1;
    }

    new Float:dx = x - AC_LastMovementX[playerid];
    new Float:dy = y - AC_LastMovementY[playerid];
    new Float:distance = floatsqroot((dx * dx) + (dy * dy));
    new Float:speed = distance * (1000.0 / float(elapsed));
    new ping = AC_GetPing(playerid);
    new Float:limit = AC_MOVEMENT_BASE_SPEED + (float(ping) * AC_MOVEMENT_PING_TOLERANCE);

    if (limit > (AC_MOVEMENT_BASE_SPEED + AC_MOVEMENT_MAX_PING_TOLERANCE))
        limit = AC_MOVEMENT_BASE_SPEED + AC_MOVEMENT_MAX_PING_TOLERANCE;

    if (speed > limit)
    {
        AC_MovementOverLimitSamples[playerid]++;
        if (AC_MovementOverLimitSamples[playerid] >= AC_MOVEMENT_REQUIRED_SAMPLES)
        {
            AC_RecordEvidence(playerid, AC_CATEGORY_MOVEMENT, 14, "sustained on-foot speed anomaly", speed);
            AC_MovementOverLimitSamples[playerid] = 0;
        }
    }
    else
    {
        AC_MovementOverLimitSamples[playerid] = 0;
    }

    AC_LastMovementX[playerid] = x;
    AC_LastMovementY[playerid] = y;
    AC_LastMovementTick[playerid] = tick;
    return 1;
}
