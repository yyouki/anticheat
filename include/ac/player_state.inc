#if defined _AC_PLAYER_STATE_INCLUDED
    #endinput
#endif
#define _AC_PLAYER_STATE_INCLUDED

stock AC_OnPlayerSpawn(playerid)
{
    return AC_NotifyLegitimateSpawn(playerid);
}

stock AC_OnPlayerDeath(playerid)
{
    AC_ResetSampling(playerid);
    return AC_NotifyLegitimateTeleport(playerid, AC_DEFAULT_GRACE_MS);
}

stock AC_OnPlayerStateChange(playerid, PLAYER_STATE:new_state, PLAYER_STATE:old_state)
{
    #pragma unused new_state, old_state
    return AC_NotifyLegitimateStateChange(playerid);
}
