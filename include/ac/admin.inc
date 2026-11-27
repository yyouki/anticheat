#if defined _AC_ADMIN_INCLUDED
    #endinput
#endif
#define _AC_ADMIN_INCLUDED

// These helpers do not implement permission checks. The host gamemode MUST
// verify the administrator's permission before calling them.
stock AC_AdminStatus(adminid, targetid)
{
    if (!IsPlayerConnected(adminid) || !IsPlayerConnected(targetid) || !AC_PlayerLoaded[targetid])
        return 0;

    new message[144];
    SendClientMessage(adminid, 0xD8D8D8FF, "---------------- Anti-Cheat ----------------");
    format(message, sizeof(message), "[AC] Player %d | account %d", targetid, AC_AccountKey[targetid]);
    SendClientMessage(adminid, 0xE05A5AFF, message);
    format(message, sizeof(message), "Suspicion: %d/100 | Strikes: %d", AC_SuspicionScore[targetid], AC_StrikeCount[targetid]);
    SendClientMessage(adminid, 0xFFFFFFFF, message);
    format(message, sizeof(message), "Ping: %d ms | Client integrity: UNKNOWN", AC_GetPing(targetid));
    SendClientMessage(adminid, 0xFFFFFFFF, message);
    SendClientMessage(adminid, 0xD8D8D8FF, "---------------------------------------------");
    return 1;
}

stock AC_AdminEvidence(adminid, targetid)
{
    if (!IsPlayerConnected(adminid) || !IsPlayerConnected(targetid) || !AC_PlayerLoaded[targetid])
        return 0;

    new message[192];
    format(message, sizeof(message), "[AC] Recent evidence for player %d:", targetid);
    SendClientMessage(adminid, 0xE05A5AFF, message);

    if (AC_EvidenceCount[targetid] == 0)
        return SendClientMessage(adminid, 0xFFFFFFFF, "No recent evidence.");

    new now = gettime();
    for (new index; index < AC_EvidenceCount[targetid]; index++)
    {
        new timestamp, category, points, ping;
        new Float:metric;
        new reason[AC_EVIDENCE_REASON_LENGTH];
        new category_name[16];

        AC_GetEvidence(targetid, index, timestamp, category, points, ping, metric, reason);
        AC_GetCategoryName(category, category_name);
        format(message, sizeof(message), "[%d s] %s +%d | ping %d | metric %.2f | %s",
            now - timestamp, category_name, points, ping, metric, reason);
        SendClientMessage(adminid, 0xFFFFFFFF, message);
    }
    return 1;
}

stock AC_AdminClear(adminid, targetid)
{
    if (!IsPlayerConnected(adminid) || !IsPlayerConnected(targetid))
        return 0;

    new accountid = AC_AccountKey[targetid];
    if (!AC_ClearPlayerReviewState(targetid))
        return 0;

    CallLocalFunction("AC_OnAdministrativeReset", "ddd", adminid, targetid, accountid);
    SendClientMessage(adminid, 0xFFFFFFFF, "Anti-cheat review state cleared.");
    return 1;
}
