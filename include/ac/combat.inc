#if defined _AC_COMBAT_INCLUDED
    #endinput
#endif
#define _AC_COMBAT_INCLUDED

stock AC_OnPlayerGiveDamage(playerid, damagedid, Float:amount)
{
#if AC_ENABLE_COMBAT_CADENCE
    if (!AC_IsMonitored(playerid) || damagedid == INVALID_PLAYER_ID || !IsPlayerConnected(damagedid))
        return 0;

    if (!AC_IsNetworkSampleReliable(playerid, AC_COMBAT_MAX_PING))
    {
        AC_LastDamageTick[playerid] = 0;
        AC_RapidDamageIntervals[playerid] = 0;
        return 0;
    }

    new tick = GetTickCount();
    if (AC_LastDamageTick[playerid] > 0)
    {
        new elapsed = tick - AC_LastDamageTick[playerid];

        // Same-target timing only; damage callbacks are inaccurate in some cases.
        if (elapsed > 0
            && elapsed < AC_COMBAT_MIN_INTERVAL_MS
            && AC_LastDamagedPlayer[playerid] == damagedid)
        {
            AC_RapidDamageIntervals[playerid]++;
        }
        else
        {
            AC_RapidDamageIntervals[playerid] = 0;
        }

        if (AC_RapidDamageIntervals[playerid] >= AC_COMBAT_REQUIRED_FAST_INTERVALS
            && (tick - AC_LastCombatEvidenceTick[playerid]) >= AC_COMBAT_EVIDENCE_COOLDOWN_MS)
        {
            AC_RecordEvidence(playerid, AC_CATEGORY_COMBAT, 10, "repeated short damage-callback cadence", float(elapsed));
            AC_LastCombatEvidenceTick[playerid] = tick;
            AC_RapidDamageIntervals[playerid] = 0;
        }
    }

    AC_LastDamageTick[playerid] = tick;
    AC_LastDamagedPlayer[playerid] = damagedid;
    #pragma unused amount
#else
    #pragma unused playerid, damagedid, amount
#endif
    return 1;
}

stock AC_OnPlayerWeaponShot(playerid, WEAPON:weaponid, BULLET_HIT_TYPE:hittype, hitid)
{
    // Raw shot callbacks are not scored in v1. They may be recorded by a
    // separate, versioned experiment after mobile/controller traces exist.
    #pragma unused playerid, weaponid, hittype, hitid
    return 1;
}
