#if defined _AC_EVIDENCE_INCLUDED
    #endinput
#endif
#define _AC_EVIDENCE_INCLUDED

stock AC_GetRecentCategoryMask(playerid)
{
    new now = gettime();
    new mask;

    for (new category; category < AC_CATEGORY_COUNT; category++)
    {
        if (AC_CategoryLastAt[playerid][category] > 0
            && (now - AC_CategoryLastAt[playerid][category]) <= AC_EVIDENCE_WINDOW_SECONDS)
        {
            mask |= (1 << category);
        }
    }
    return mask;
}

stock AC_GetCategoryName(category, destination[], size = sizeof(destination))
{
    static const names[AC_CATEGORY_COUNT][] = {
        "movement", "vehicle", "combat", "state", "integrity"
    };

    if (category < 0 || category >= AC_CATEGORY_COUNT)
        return format(destination, size, "unknown");

    return format(destination, size, "%s", names[category]);
}

stock AC_RecordEvidence(playerid, category, points, const reason[], Float:metric = 0.0)
{
    if (!AC_IsMonitored(playerid)
        || category < 0
        || category >= AC_CATEGORY_COUNT
        || points <= 0)
    {
        return 0;
    }

    new now = gettime();
    if (AC_CategoryLastAt[playerid][category] > 0
        && (now - AC_CategoryLastAt[playerid][category]) < AC_CATEGORY_COOLDOWN_SECONDS)
    {
        return 0;
    }

    new recent_mask = AC_GetRecentCategoryMask(playerid);
    new other_mask = recent_mask & ~(1 << category);
    new correlated_count;

    for (new index; index < AC_CATEGORY_COUNT; index++)
    {
        if (other_mask & (1 << index))
            correlated_count++;
    }

    new adjusted_points = points + (correlated_count * 3);
    if (adjusted_points > points + 9)
        adjusted_points = points + 9;

    AC_CategoryLastAt[playerid][category] = now;

    new slot = AC_EvidenceHead[playerid];
    AC_EvidenceTime[playerid][slot] = now;
    AC_EvidenceCategory[playerid][slot] = category;
    AC_EvidencePoints[playerid][slot] = adjusted_points;
    AC_EvidencePing[playerid][slot] = AC_GetPing(playerid);
    AC_EvidenceMetric[playerid][slot] = metric;
    format(AC_EvidenceReason[playerid][slot], AC_EVIDENCE_REASON_LENGTH, "%s", reason);

    AC_EvidenceHead[playerid] = (slot + 1) % AC_MAX_EVIDENCE;
    if (AC_EvidenceCount[playerid] < AC_MAX_EVIDENCE)
        AC_EvidenceCount[playerid]++;

    AC_SuspicionScore[playerid] += adjusted_points;
    if (AC_SuspicionScore[playerid] > 100)
        AC_SuspicionScore[playerid] = 100;

    AC_Dirty[playerid] = true;
    CallLocalFunction("AC_OnEvidence", "ddddsf",
        playerid, category, adjusted_points, AC_GetPing(playerid), reason, metric
    );

    if (AC_SuspicionScore[playerid] >= AC_SCORE_STRIKE_THRESHOLD
        && other_mask != 0
        && (AC_LastStrikeAt[playerid] == 0
            || (now - AC_LastStrikeAt[playerid]) >= AC_STRIKE_COOLDOWN_SECONDS))
    {
        AC_StrikeCount[playerid]++;
        AC_LastStrikeAt[playerid] = now;
        AC_LastStrikeDecayAt[playerid] = now;

        AC_SuspicionScore[playerid] -= AC_SCORE_STRIKE_REDUCTION;
        if (AC_SuspicionScore[playerid] < 0)
            AC_SuspicionScore[playerid] = 0;

        AC_Dirty[playerid] = true;
        CallLocalFunction("AC_OnStrike", "ddds",
            playerid, AC_AccountKey[playerid], AC_StrikeCount[playerid], reason
        );
        AC_SavePersistentState(playerid);
    }
    return 1;
}

stock AC_GetSuspicionScore(playerid)
{
    return AC_SuspicionScore[playerid];
}

stock AC_GetStrikeCount(playerid)
{
    return AC_StrikeCount[playerid];
}

stock AC_GetEvidenceCount(playerid)
{
    return AC_EvidenceCount[playerid];
}

stock AC_GetEvidence(playerid, index, &timestamp, &category, &points, &ping, &Float:metric, reason[], size = sizeof(reason))
{
    if (index < 0 || index >= AC_EvidenceCount[playerid])
        return 0;

    new slot = (AC_EvidenceHead[playerid] - AC_EvidenceCount[playerid] + index + AC_MAX_EVIDENCE) % AC_MAX_EVIDENCE;
    timestamp = AC_EvidenceTime[playerid][slot];
    category = AC_EvidenceCategory[playerid][slot];
    points = AC_EvidencePoints[playerid][slot];
    ping = AC_EvidencePing[playerid][slot];
    metric = AC_EvidenceMetric[playerid][slot];
    format(reason, size, "%s", AC_EvidenceReason[playerid][slot]);
    return 1;
}

stock AC_ClearPlayerEvidence(playerid)
{
    AC_ResetEvidence(playerid);
    return 1;
}

stock AC_ClearPlayerReviewState(playerid)
{
    if (!AC_PlayerLoaded[playerid])
        return 0;

    AC_SuspicionScore[playerid] = 0;
    AC_StrikeCount[playerid] = 0;
    AC_LastScoreDecayAt[playerid] = gettime();
    AC_LastStrikeDecayAt[playerid] = gettime();
    AC_LastStrikeAt[playerid] = 0;
    AC_ResetEvidence(playerid);
    AC_Dirty[playerid] = true;
    AC_SavePersistentState(playerid);
    return 1;
}
