#if defined _AC_VEHICLE_INCLUDED
    #endinput
#endif
#define _AC_VEHICLE_INCLUDED

stock bool:AC_IsExcludedVehicleModel(modelid)
{
    // These classes need different movement envelopes and are not scored by v1.
    switch (modelid)
    {
        case 417, 425, 430, 446, 447, 452, 453, 454, 460, 464, 469, 472, 473,
             476, 484, 487, 488, 493, 497, 500, 501, 502, 503, 511, 512, 513,
             519, 520, 537, 538, 548, 553, 563, 577, 592, 593, 595:
        {
            return true;
        }
    }
    return false;
}

stock AC_OnVehicleSample(playerid)
{
    if (!AC_IsValidPlayerId(playerid))
        return 0;
    if (!AC_IsMonitored(playerid) || GetPlayerState(playerid) != PLAYER_STATE_DRIVER)
    {
        AC_VehicleOverLimitSamples[playerid] = 0;
        AC_LastVehicleId[playerid] = INVALID_VEHICLE_ID;
        return 0;
    }

    if (!AC_IsNetworkSampleReliable(playerid, AC_VEHICLE_MAX_PING))
    {
        AC_VehicleOverLimitSamples[playerid] = 0;
        AC_LastVehicleId[playerid] = INVALID_VEHICLE_ID;
        return 0;
    }

    new vehicleid = GetPlayerVehicleID(playerid);
    if (vehicleid == 0 || vehicleid == INVALID_VEHICLE_ID || !IsValidVehicle(vehicleid))
    {
        AC_VehicleOverLimitSamples[playerid] = 0;
        AC_LastVehicleId[playerid] = INVALID_VEHICLE_ID;
        return 0;
    }

    if (AC_IsInGrace(playerid))
    {
        AC_VehicleOverLimitSamples[playerid] = 0;
        AC_LastVehicleId[playerid] = vehicleid;
        return 1;
    }

    if (vehicleid != AC_LastVehicleId[playerid])
    {
        AC_LastVehicleId[playerid] = vehicleid;
        AC_VehicleOverLimitSamples[playerid] = 0;
        return 1;
    }

    if (AC_IsExcludedVehicleModel(GetVehicleModel(vehicleid)))
    {
        AC_VehicleOverLimitSamples[playerid] = 0;
        return 0;
    }

    new Float:vx, Float:vy, Float:vz;
    if (!GetVehicleVelocity(vehicleid, vx, vy, vz))
        return 0;

    new Float:speed = floatsqroot((vx * vx) + (vy * vy) + (vz * vz)) * AC_VEHICLE_SPEED_FACTOR;
    new ping = AC_GetPing(playerid);
    new Float:limit = AC_VEHICLE_MAX_SPEED_KMH + (float(ping) * AC_VEHICLE_PING_TOLERANCE);

    if (limit > (AC_VEHICLE_MAX_SPEED_KMH + AC_VEHICLE_MAX_PING_TOLERANCE))
        limit = AC_VEHICLE_MAX_SPEED_KMH + AC_VEHICLE_MAX_PING_TOLERANCE;

    if (speed > limit)
    {
        AC_VehicleOverLimitSamples[playerid]++;
        if (AC_VehicleOverLimitSamples[playerid] >= AC_VEHICLE_REQUIRED_SAMPLES)
        {
            AC_RecordEvidence(playerid, AC_CATEGORY_VEHICLE, 18, "sustained vehicle speed anomaly", speed);
            AC_VehicleOverLimitSamples[playerid] = 0;
        }
    }
    else
    {
        AC_VehicleOverLimitSamples[playerid] = 0;
    }
    return 1;
}
