#include <ac>

main()
{
}

public OnGameModeInit()
{
    AC_Init();
    print("[AC] Standalone framework smoke gamemode loaded.");
    return 1;
}

public OnPlayerConnect(playerid)
{
    AC_OnPlayerConnect(playerid);
    return 1;
}

public OnPlayerDisconnect(playerid, reason)
{
    #pragma unused reason
    AC_OnPlayerDisconnect(playerid);
    return 1;
}

public OnPlayerSpawn(playerid)
{
    AC_OnPlayerSpawn(playerid);
    return 1;
}

public OnPlayerDeath(playerid, killerid, WEAPON:reason)
{
    #pragma unused killerid, reason
    AC_OnPlayerDeath(playerid);
    return 1;
}

public OnPlayerStateChange(playerid, PLAYER_STATE:newstate, PLAYER_STATE:oldstate)
{
    AC_OnPlayerStateChange(playerid, newstate, oldstate);
    return 1;
}

public OnPlayerUpdate(playerid)
{
    AC_OnPlayerUpdate(playerid);
    return 1;
}

public OnPlayerGiveDamage(playerid, damagedid, Float:amount, WEAPON:weaponid, bodypart)
{
    #pragma unused weaponid, bodypart
    AC_OnPlayerGiveDamage(playerid, damagedid, amount);
    return 1;
}

public OnPlayerWeaponShot(playerid, WEAPON:weaponid, BULLET_HIT_TYPE:hittype, hitid, Float:fX, Float:fY, Float:fZ)
{
    #pragma unused fX, fY, fZ
    AC_OnPlayerWeaponShot(playerid, weaponid, hittype, hitid);
    return 1;
}

public OnClientCheckResponse(playerid, actionid, memaddr, retndata)
{
    AC_OnClientCheckResponse(playerid, actionid, memaddr, retndata);
    return 1;
}

public AC_OnEvidence(playerid, category, points, ping, const reason[], Float:metric)
{
    #pragma unused playerid, category, points, ping, reason, metric
    return 1;
}

public AC_OnStrike(playerid, accountid, strikes, const reason[])
{
    #pragma unused playerid, accountid, strikes, reason
    return 1;
}

// Call this from the gamemode's real, successful login/character activation path.
// Do not enable monitoring before authentication and character state are ready.
stock AC_ExampleOnAuthenticated(playerid, accountid)
{
    AC_SetIdentity(playerid, accountid);
    AC_NotifyLegitimateSpawn(playerid);
    return 1;
}

// Call this before every server-controlled SetPlayerPos / SetPlayerPosEx path.
stock AC_ExampleOnLegitimateTeleport(playerid)
{
    AC_NotifyLegitimateTeleport(playerid);
    return 1;
}
