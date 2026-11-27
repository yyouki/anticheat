#if defined _AC_INTEGRITY_INCLUDED
    #endinput
#endif
#define _AC_INTEGRITY_INCLUDED

stock bool:AC_RequestClientIntegrityCheck(playerid)
{
    if (!AC_IsMonitored(playerid))
        return false;

#if AC_ENABLE_CLIENT_MEMORY_CHECKS
    // Deliberately empty until explicit per-client-version profiles are reviewed.
    // Never send generic memory addresses or punish missing/unknown responses.
#endif
    return false;
}

stock AC_OnClientCheckResponse(playerid, actionid, memaddr, retndata)
{
    // Response is telemetry only until a matching signed/versioned profile exists.
    #pragma unused playerid, actionid, memaddr, retndata
    return 1;
}

stock AC_GetClientIntegrityStatus(playerid)
{
    // 0 = not checked / unknown. Unknown is not a cheat verdict.
    #pragma unused playerid
    return 0;
}
