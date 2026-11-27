#include <ac>

#define AC_STAGE_STORE_CAPACITY (MAX_PLAYERS)

new AC_StageSavedAccountId[AC_STAGE_STORE_CAPACITY];
new AC_StageSavedScore[AC_STAGE_STORE_CAPACITY];
new AC_StageSavedStrikes[AC_STAGE_STORE_CAPACITY];
new AC_StageSavedScoreDecayAt[AC_STAGE_STORE_CAPACITY];
new AC_StageSavedStrikeDecayAt[AC_STAGE_STORE_CAPACITY];
new AC_StageSavedLastStrikeAt[AC_STAGE_STORE_CAPACITY];
new AC_StageVehicleId[MAX_PLAYERS];

stock AC_StageFindSavedSlot(accountid)
{
    if (accountid <= 0)
        return -1;

    for (new slot; slot < AC_STAGE_STORE_CAPACITY; slot++)
    {
        if (AC_StageSavedAccountId[slot] == accountid)
            return slot;
    }
    return -1;
}

stock AC_StageGetOrCreateSavedSlot(accountid)
{
    new slot = AC_StageFindSavedSlot(accountid);
    if (slot != -1)
        return slot;

    for (new index; index < AC_STAGE_STORE_CAPACITY; index++)
    {
        if (AC_StageSavedAccountId[index] == 0)
        {
            AC_StageSavedAccountId[index] = accountid;
            return index;
        }
    }
    return -1;
}

stock AC_StageParseAccountId(const value[])
{
    new length = strlen(value);
    if (length == 0 || length > 10)
        return 0;

    new result;
    for (new index; index < length; index++)
    {
        if (value[index] < '0' || value[index] > '9')
            return 0;

        new digit = value[index] - '0';
        if (result > (2147483647 - digit) / 10)
            return 0;

        result = (result * 10) + digit;
    }
    return result;
}

stock AC_StageRequireLoaded(playerid)
{
    if (!AC_IsValidPlayerId(playerid) || !IsPlayerConnected(playerid))
        return 0;

    if (!AC_PlayerLoaded[playerid])
    {
        SendClientMessage(playerid, 0xE05A5AFF, "[AC-STAGE] Authenticate first: /acstageauth <accountid>");
        return 0;
    }
    return 1;
}

stock AC_StageAuthenticate(playerid, accountid)
{
    if (!AC_IsValidPlayerId(playerid) || !IsPlayerConnected(playerid) || accountid <= 0)
        return 0;

    if (AC_PlayerLoaded[playerid])
    {
        SendClientMessage(playerid, 0xE05A5AFF, "[AC-STAGE] Already authenticated. Reconnect before switching test accounts.");
        return 0;
    }

    new sessiontoken = AC_BeginAccountLoad(playerid, accountid);
    if (sessiontoken <= 0)
    {
        SendClientMessage(playerid, 0xE05A5AFF, "[AC-STAGE] Could not begin the test account load.");
        return 0;
    }

    new score;
    new strikes;
    new score_decay_at = gettime();
    new strike_decay_at = gettime();
    new last_strike_at;

    new slot = AC_StageFindSavedSlot(accountid);
    if (slot != -1)
    {
        score = AC_StageSavedScore[slot];
        strikes = AC_StageSavedStrikes[slot];
        score_decay_at = AC_StageSavedScoreDecayAt[slot];
        strike_decay_at = AC_StageSavedStrikeDecayAt[slot];
        last_strike_at = AC_StageSavedLastStrikeAt[slot];
    }

    if (!AC_ApplyPersistentState(
        playerid,
        accountid,
        sessiontoken,
        score,
        strikes,
        score_decay_at,
        strike_decay_at,
        last_strike_at
    ))
    {
        SendClientMessage(playerid, 0xE05A5AFF, "[AC-STAGE] Test account state was rejected.");
        return 0;
    }

    if (slot == -1)
    {
        SendClientMessage(playerid, 0xD8D8D8FF, "[AC-STAGE] New in-memory test account loaded.");
    }
    else
    {
        SendClientMessage(playerid, 0xD8D8D8FF, "[AC-STAGE] Saved in-memory test account restored.");
    }

    printf("[AC-STAGE] LOAD account=%d session=%d score=%d strikes=%d",
        accountid, sessiontoken, score, strikes);
    SendClientMessage(playerid, 0xD8D8D8FF, "[AC-STAGE] Use /acstagehelp to list test commands.");
    return 1;
}

stock AC_StageShowInfo(playerid)
{
    if (!AC_StageRequireLoaded(playerid))
        return 0;

    new message[144];
    new enabled_text[4];

    if (AC_PlayerEnabled[playerid])
        format(enabled_text, sizeof(enabled_text), "yes");
    else
        format(enabled_text, sizeof(enabled_text), "no");

    format(message, sizeof(message), "[AC-STAGE] Account %d | monitoring: %s",
        AC_AccountKey[playerid], enabled_text);
    SendClientMessage(playerid, 0xD8D8D8FF, message);

    format(message, sizeof(message), "[AC-STAGE] Score: %d/100 | strikes: %d | evidence: %d",
        AC_GetSuspicionScore(playerid),
        AC_GetStrikeCount(playerid),
        AC_GetEvidenceCount(playerid));
    SendClientMessage(playerid, 0xD8D8D8FF, message);
    return 1;
}

stock AC_StageShowEvidence(playerid)
{
    if (!AC_StageRequireLoaded(playerid))
        return 0;

    new count = AC_GetEvidenceCount(playerid);
    if (count == 0)
    {
        SendClientMessage(playerid, 0xD8D8D8FF, "[AC-STAGE] No evidence records in this session.");
        return 1;
    }

    new message[144];
    for (new index; index < count; index++)
    {
        new timestamp, category, points, ping;
        new Float:metric;
        new reason[AC_EVIDENCE_REASON_LENGTH];
        new category_name[16];

        if (!AC_GetEvidence(
            playerid, index, timestamp, category, points, ping, metric, reason, sizeof(reason)
        ))
            continue;

        AC_GetCategoryName(category, category_name, sizeof(category_name));
        format(message, sizeof(message), "[AC-STAGE] %s +%d | ping %d | %s",
            category_name, points, ping, reason);
        SendClientMessage(playerid, 0xD8D8D8FF, message);
    }
    return 1;
}

stock AC_StageDestroyVehicle(playerid)
{
    if (!AC_IsValidPlayerId(playerid))
        return 0;

    new vehicleid = AC_StageVehicleId[playerid];
    if (vehicleid != 0 && vehicleid != INVALID_VEHICLE_ID && IsValidVehicle(vehicleid))
        DestroyVehicle(vehicleid);

    AC_StageVehicleId[playerid] = INVALID_VEHICLE_ID;
    return 1;
}

#define AC_STAGE_SELFTEST_ACCOUNT_BASE (2000000000)

stock AC_StageSelfTestCheck(playerid, bool:condition, const label[])
{
    new message[112];

    if (condition)
    {
        format(message, sizeof(message), "[AC-STAGE-TEST] PASS: %s", label);
        printf("%s", message);
        SendClientMessage(playerid, 0x70D890FF, message);
        return 1;
    }

    format(message, sizeof(message), "[AC-STAGE-TEST] FAIL: %s", label);
    printf("%s", message);
    SendClientMessage(playerid, 0xE05A5AFF, message);
    return 0;
}

stock AC_StageRestoreAccountAfterSelfTest(playerid, accountid)
{
    // Simulate a fresh framework session without disconnecting the real game client.
    AC_OnPlayerDisconnect(playerid);
    AC_OnPlayerConnect(playerid);
    return AC_StageAuthenticate(playerid, accountid);
}

stock AC_StageRunPersistenceSelfTest(playerid)
{
    if (!AC_StageRequireLoaded(playerid))
        return 0;

    new original_accountid = AC_AccountKey[playerid];
    new selftest_accountid = AC_STAGE_SELFTEST_ACCOUNT_BASE + playerid;
    if (selftest_accountid == original_accountid)
        selftest_accountid++;

    // Reserve both records before mutating the active player session.
    if (AC_StageGetOrCreateSavedSlot(original_accountid) == -1
        || AC_StageGetOrCreateSavedSlot(selftest_accountid) == -1)
    {
        SendClientMessage(playerid, 0xE05A5AFF, "[AC-STAGE-TEST] Not enough in-memory account slots.");
        return 0;
    }

    if (!AC_SavePersistentState(playerid))
    {
        SendClientMessage(playerid, 0xE05A5AFF, "[AC-STAGE-TEST] Could not preserve your current test account.");
        return 0;
    }

    new passed;
    new failed;
    new now = gettime();
    new score = 27;
    new strikes = 3;
    new score_decay_at = now;
    new strike_decay_at = now;
    new last_strike_at = now - 60;
    new sessiontoken = AC_BeginAccountLoad(playerid, selftest_accountid);

    if (sessiontoken <= 0)
    {
        SendClientMessage(playerid, 0xE05A5AFF, "[AC-STAGE-TEST] Could not begin synthetic self-test load.");
        AC_StageRestoreAccountAfterSelfTest(playerid, original_accountid);
        return 0;
    }

    new stale_token = sessiontoken - 1;
    if (stale_token <= 0)
        stale_token = sessiontoken + 1;

    if (AC_StageSelfTestCheck(
        playerid,
        !AC_ApplyPersistentState(
            playerid, selftest_accountid, stale_token,
            score, strikes, score_decay_at, strike_decay_at, last_strike_at
        ),
        "stale session token rejected"
    ))
        passed++;
    else
        failed++;

    if (AC_StageSelfTestCheck(
        playerid,
        !AC_ApplyPersistentState(
            playerid, selftest_accountid + 1, sessiontoken,
            score, strikes, score_decay_at, strike_decay_at, last_strike_at
        ),
        "account ID mismatch rejected"
    ))
        passed++;
    else
        failed++;

    if (!AC_ApplyPersistentState(
        playerid,
        selftest_accountid,
        sessiontoken,
        score,
        strikes,
        score_decay_at,
        strike_decay_at,
        last_strike_at
    ))
    {
        AC_StageSelfTestCheck(playerid, false, "valid account state accepted");
        failed++;
        AC_StageRestoreAccountAfterSelfTest(playerid, original_accountid);
        return 0;
    }

    if (AC_StageSelfTestCheck(
        playerid,
        AC_PlayerLoaded[playerid] && AC_PlayerEnabled[playerid],
        "valid account load enables monitoring"
    ))
        passed++;
    else
        failed++;

    if (AC_StageSelfTestCheck(
        playerid,
        !AC_ApplyPersistentState(
            playerid, selftest_accountid, sessiontoken,
            score, strikes, score_decay_at, strike_decay_at, last_strike_at
        ),
        "duplicate account load rejected"
    ))
        passed++;
    else
        failed++;

    if (AC_StageSelfTestCheck(
        playerid,
        AC_LastStrikeAt[playerid] == last_strike_at
            && AC_LastStrikeAt[playerid] != AC_LastStrikeDecayAt[playerid],
        "strike cooldown timestamp remains separate"
    ))
        passed++;
    else
        failed++;

    AC_NotifyLegitimateTeleport(playerid);
    if (AC_StageSelfTestCheck(playerid, AC_IsInGrace(playerid), "legal transition starts grace window"))
        passed++;
    else
        failed++;

    AC_NotifyLegitimateVehicleChange(playerid);
    if (AC_StageSelfTestCheck(playerid, true, "vehicle transition notification accepted"))
        passed++;
    else
        failed++;

    if (AC_SavePersistentState(playerid))
    {
        if (AC_StageSelfTestCheck(
            playerid,
            AC_StageSavedScore[AC_StageFindSavedSlot(selftest_accountid)] == score
                && AC_StageSavedStrikes[AC_StageFindSavedSlot(selftest_accountid)] == strikes
                && AC_StageSavedLastStrikeAt[AC_StageFindSavedSlot(selftest_accountid)] == last_strike_at,
            "persistence callback saves score, strikes and cooldown timestamp"
        ))
            passed++;
        else
            failed++;
    }
    else
    {
        AC_StageSelfTestCheck(playerid, false, "persistence callback accepts save");
        failed++;
    }

    // Exercise the framework's disconnect/connect reset path while keeping this
    // client connected; this is not a substitute for a real network reconnect.
    AC_OnPlayerDisconnect(playerid);
    AC_OnPlayerConnect(playerid);
    if (AC_StageAuthenticate(playerid, selftest_accountid))
    {
        new restored = AC_StageSelfTestCheck(
            playerid,
            AC_GetSuspicionScore(playerid) == score
                && AC_GetStrikeCount(playerid) == strikes
                && AC_LastStrikeAt[playerid] == last_strike_at,
            "saved state restored after simulated session reconnect"
        );
        if (restored)
            passed++;
        else
            failed++;
    }
    else
    {
        AC_StageSelfTestCheck(playerid, false, "saved state restored after simulated session reconnect");
        failed++;
    }

    if (!AC_StageRestoreAccountAfterSelfTest(playerid, original_accountid))
    {
        AC_StageSelfTestCheck(playerid, false, "original synthetic account restored");
        failed++;
    }
    else
    {
        if (AC_StageSelfTestCheck(
            playerid,
            AC_PlayerLoaded[playerid] && AC_AccountKey[playerid] == original_accountid,
            "original synthetic account restored"
        ))
            passed++;
        else
            failed++;
    }

    new summary[96];
    format(summary, sizeof(summary), "[AC-STAGE-TEST] Finished: %d passed, %d failed.", passed, failed);
    SendClientMessage(playerid, failed == 0 ? 0x70D890FF : 0xE05A5AFF, summary);
    printf("%s", summary);
    return failed == 0;
}

public OnGameModeInit()
{
    AC_Init();
    SetGameModeText("Anti-Cheat Staging");
    AddPlayerClass(0, 1958.3783, 1343.1572, 15.3746, 269.1425, WEAPON_FIST, 0, WEAPON_FIST, 0, WEAPON_FIST, 0);

    print("[AC-STAGE] Staging gamemode initialized.");
    print("[AC-STAGE] Persistence is intentionally in-memory and is lost on server restart.");
    return 1;
}

public OnPlayerConnect(playerid)
{
    AC_OnPlayerConnect(playerid);
    AC_StageVehicleId[playerid] = INVALID_VEHICLE_ID;
    SendClientMessage(playerid, 0xD8D8D8FF, "[AC-STAGE] Monitoring is off until you authenticate.");
    SendClientMessage(playerid, 0xD8D8D8FF, "[AC-STAGE] Authenticate with /acstageauth <accountid>.");
    return 1;
}

public OnPlayerDisconnect(playerid, reason)
{
    #pragma unused reason
    AC_StageDestroyVehicle(playerid);
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

public OnPlayerCommandText(playerid, cmdtext[])
{
    if (!strcmp(cmdtext, "/acstagehelp", true))
    {
        SendClientMessage(playerid, 0xE05A5AFF, "Anti-Cheat staging commands:");
        SendClientMessage(playerid, 0xD8D8D8FF, "/acstageauth <accountid> - load a synthetic test account");
        SendClientMessage(playerid, 0xD8D8D8FF, "/acstageinfo - show monitoring and score state");
        SendClientMessage(playerid, 0xD8D8D8FF, "/acstagetest - run session and persistence self-tests");
        SendClientMessage(playerid, 0xD8D8D8FF, "/acstageevidence - show current evidence records");
        SendClientMessage(playerid, 0xD8D8D8FF, "/acstagetoggle - enable or disable monitoring");
        SendClientMessage(playerid, 0xD8D8D8FF, "/acstagesave - save to the temporary memory adapter");
        SendClientMessage(playerid, 0xD8D8D8FF, "/acstageclear - clear your own review state");
        SendClientMessage(playerid, 0xD8D8D8FF, "/acstageteleport - test a server-notified legal teleport");
        SendClientMessage(playerid, 0xD8D8D8FF, "/acstagevehicle - spawn and enter a test vehicle");
        SendClientMessage(playerid, 0xD8D8D8FF, "/acstageexitvehicle - leave your current vehicle");
        return 1;
    }

    if (!strcmp(cmdtext, "/acstageauth", true))
    {
        SendClientMessage(playerid, 0xE05A5AFF, "Usage: /acstageauth <positive synthetic account ID>");
        return 1;
    }

    if (strfind(cmdtext, "/acstageauth ", true) == 0)
    {
        new accountid = AC_StageParseAccountId(cmdtext[13]);
        if (accountid <= 0)
        {
            SendClientMessage(playerid, 0xE05A5AFF, "[AC-STAGE] Account ID must be a positive integer.");
            return 1;
        }

        AC_StageAuthenticate(playerid, accountid);
        return 1;
    }

    if (!strcmp(cmdtext, "/acstagetest", true))
    {
        AC_StageRunPersistenceSelfTest(playerid);
        return 1;
    }

    if (!strcmp(cmdtext, "/acstageinfo", true))
    {
        AC_StageShowInfo(playerid);
        return 1;
    }

    if (!strcmp(cmdtext, "/acstageevidence", true))
    {
        AC_StageShowEvidence(playerid);
        return 1;
    }

    if (!strcmp(cmdtext, "/acstagetoggle", true))
    {
        if (!AC_StageRequireLoaded(playerid))
            return 1;

        new bool:enabled = !AC_PlayerEnabled[playerid];
        if (AC_SetEnabled(playerid, enabled))
        {
            if (enabled)
                SendClientMessage(playerid, 0xD8D8D8FF, "[AC-STAGE] Monitoring enabled.");
            else
                SendClientMessage(playerid, 0xD8D8D8FF, "[AC-STAGE] Monitoring disabled.");
        }
        return 1;
    }

    if (!strcmp(cmdtext, "/acstagesave", true))
    {
        if (!AC_StageRequireLoaded(playerid))
            return 1;

        if (AC_SavePersistentState(playerid))
            SendClientMessage(playerid, 0xD8D8D8FF, "[AC-STAGE] Save accepted by the in-memory adapter.");
        else
            SendClientMessage(playerid, 0xE05A5AFF, "[AC-STAGE] Save was not accepted.");
        return 1;
    }

    if (!strcmp(cmdtext, "/acstageclear", true))
    {
        if (!AC_StageRequireLoaded(playerid))
            return 1;

        if (AC_ClearPlayerReviewState(playerid))
            SendClientMessage(playerid, 0xD8D8D8FF, "[AC-STAGE] Your review state was cleared.");
        else
            SendClientMessage(playerid, 0xE05A5AFF, "[AC-STAGE] Review state could not be cleared.");
        return 1;
    }

    if (!strcmp(cmdtext, "/acstageteleport", true))
    {
        if (!AC_StageRequireLoaded(playerid))
            return 1;

        new Float:x, Float:y, Float:z;
        if (!GetPlayerPos(playerid, x, y, z))
            return 1;

        // Notify the detector before moving the player through a server-owned action.
        AC_NotifyLegitimateTeleport(playerid);
        SetPlayerPos(playerid, x + 8.0, y, z);
        SendClientMessage(playerid, 0xD8D8D8FF, "[AC-STAGE] Legal teleport applied with a grace window.");
        return 1;
    }

    if (!strcmp(cmdtext, "/acstagevehicle", true))
    {
        if (!AC_StageRequireLoaded(playerid))
            return 1;

        new Float:x, Float:y, Float:z;
        if (!GetPlayerPos(playerid, x, y, z))
            return 1;

        AC_StageDestroyVehicle(playerid);
        new vehicleid = CreateVehicle(411, x + 5.0, y, z, 0.0, -1, -1, 60);
        if (vehicleid == 0 || vehicleid == INVALID_VEHICLE_ID)
        {
            SendClientMessage(playerid, 0xE05A5AFF, "[AC-STAGE] Could not create the test vehicle.");
            return 1;
        }

        AC_StageVehicleId[playerid] = vehicleid;
        PutPlayerInVehicle(playerid, vehicleid, 0);
        AC_NotifyLegitimateVehicleChange(playerid);
        SendClientMessage(playerid, 0xD8D8D8FF, "[AC-STAGE] Test vehicle created and server-placed.");
        return 1;
    }

    if (!strcmp(cmdtext, "/acstageexitvehicle", true))
    {
        if (!AC_StageRequireLoaded(playerid))
            return 1;

        if (GetPlayerState(playerid) == PLAYER_STATE_DRIVER
            || GetPlayerState(playerid) == PLAYER_STATE_PASSENGER)
        {
            RemovePlayerFromVehicle(playerid);
            AC_NotifyLegitimateVehicleChange(playerid);
            SendClientMessage(playerid, 0xD8D8D8FF, "[AC-STAGE] Vehicle exit completed.");
        }
        else
        {
            SendClientMessage(playerid, 0xE05A5AFF, "[AC-STAGE] You are not in a vehicle.");
        }
        return 1;
    }

    return 0;
}

public AC_OnPersistenceSave(playerid, accountid, score, strikes, score_decay_at, strike_decay_at, last_strike_at)
{
    if (!AC_IsValidPlayerId(playerid)
        || !IsPlayerConnected(playerid)
        || !AC_PlayerLoaded[playerid]
        || AC_AccountKey[playerid] != accountid
        || accountid <= 0)
    {
        return 0;
    }

    new slot = AC_StageGetOrCreateSavedSlot(accountid);
    if (slot == -1)
    {
        print("[AC-STAGE] In-memory account store is full; persistence callback rejected the save.");
        return 0;
    }

    AC_StageSavedScore[slot] = score;
    AC_StageSavedStrikes[slot] = strikes;
    AC_StageSavedScoreDecayAt[slot] = score_decay_at;
    AC_StageSavedStrikeDecayAt[slot] = strike_decay_at;
    AC_StageSavedLastStrikeAt[slot] = last_strike_at;

    printf("[AC-STAGE] SAVE account=%d score=%d strikes=%d", accountid, score, strikes);
    return 1;
}

public AC_OnEvidence(playerid, category, points, ping, const reason[], Float:metric)
{
    #pragma unused metric
    new category_name[16];
    AC_GetCategoryName(category, category_name, sizeof(category_name));
    printf("[AC-STAGE] EVIDENCE player=%d category=%s points=%d ping=%d reason=%s",
        playerid, category_name, points, ping, reason);
    return 1;
}

public AC_OnStrike(playerid, accountid, strikes, const reason[])
{
    printf("[AC-STAGE] REVIEW_MARKER player=%d account=%d strikes=%d reason=%s",
        playerid, accountid, strikes, reason);
    return 1;
}

public AC_OnAdministrativeReset(adminid, targetid, accountid)
{
    printf("[AC-STAGE] REVIEW_RESET actor=%d target=%d account=%d",
        adminid, targetid, accountid);
    return 1;
}
