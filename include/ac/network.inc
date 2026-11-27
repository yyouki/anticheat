#if defined _AC_NETWORK_INCLUDED
    #endinput
#endif
#define _AC_NETWORK_INCLUDED

#define AC_NETWORK_QUALITY_TTL_MS (3000)

stock AC_SetNetworkQuality(playerid, ping, Float:packet_loss)
{
    if (!AC_IsValidPlayerId(playerid) || !IsPlayerConnected(playerid))
        return 0;

    AC_NetworkPing[playerid] = ping;
    AC_NetworkQualityTick[playerid] = GetTickCount();
    AC_NetworkPacketLossKnown[playerid] = true;

    if (packet_loss < 0.0) packet_loss = 0.0;
    if (packet_loss > 100.0) packet_loss = 100.0;
    AC_NetworkPacketLoss[playerid] = packet_loss;
    return 1;
}

stock AC_GetPing(playerid)
{
    if (!AC_IsValidPlayerId(playerid) || !IsPlayerConnected(playerid))
        return -1;

    if (AC_NetworkQualityTick[playerid] > 0
        && (GetTickCount() - AC_NetworkQualityTick[playerid]) <= AC_NETWORK_QUALITY_TTL_MS)
    {
        return AC_NetworkPing[playerid];
    }
    return GetPlayerPing(playerid);
}

stock bool:AC_IsNetworkSampleReliable(playerid, max_ping)
{
    new ping = AC_GetPing(playerid);
    if (ping < 0 || ping == 65535 || ping > max_ping)
        return false;

    // Packet loss is optional. Severe loss suppresses evidence rather than
    // increasing suspicion. The host may provide it from a validated source.
    if (AC_NetworkPacketLossKnown[playerid]
        && (GetTickCount() - AC_NetworkQualityTick[playerid]) <= AC_NETWORK_QUALITY_TTL_MS
        && AC_NetworkPacketLoss[playerid] >= 15.0)
    {
        return false;
    }
    return true;
}
