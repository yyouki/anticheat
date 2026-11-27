#if defined _AC_STATE_INCLUDED
    #endinput
#endif
#define _AC_STATE_INCLUDED

new bool:AC_Initialized;
new AC_SessionToken[MAX_PLAYERS];
new bool:AC_PlayerLoaded[MAX_PLAYERS];
new bool:AC_PlayerEnabled[MAX_PLAYERS];
new AC_AccountKey[MAX_PLAYERS];
new AC_SuspicionScore[MAX_PLAYERS];
new AC_StrikeCount[MAX_PLAYERS];
new AC_LastScoreDecayAt[MAX_PLAYERS];
new AC_LastStrikeDecayAt[MAX_PLAYERS];
new AC_LastStrikeAt[MAX_PLAYERS];
new AC_LastPersistAt[MAX_PLAYERS];
new bool:AC_Dirty[MAX_PLAYERS];

new AC_CategoryLastAt[MAX_PLAYERS][AC_CATEGORY_COUNT];
new AC_EvidenceHead[MAX_PLAYERS];
new AC_EvidenceCount[MAX_PLAYERS];
new AC_EvidenceTime[MAX_PLAYERS][AC_MAX_EVIDENCE];
new AC_EvidenceCategory[MAX_PLAYERS][AC_MAX_EVIDENCE];
new AC_EvidencePoints[MAX_PLAYERS][AC_MAX_EVIDENCE];
new AC_EvidencePing[MAX_PLAYERS][AC_MAX_EVIDENCE];
new Float:AC_EvidenceMetric[MAX_PLAYERS][AC_MAX_EVIDENCE];
new AC_EvidenceReason[MAX_PLAYERS][AC_MAX_EVIDENCE][AC_EVIDENCE_REASON_LENGTH];

new AC_GraceStartedTick[MAX_PLAYERS];
new AC_GraceDurationMs[MAX_PLAYERS];
new AC_LastUpdateTick[MAX_PLAYERS];
new AC_LastMovementTick[MAX_PLAYERS];
new bool:AC_HasMovementSample[MAX_PLAYERS];
new Float:AC_LastMovementX[MAX_PLAYERS];
new Float:AC_LastMovementY[MAX_PLAYERS];
new AC_LastMovementInterior[MAX_PLAYERS];
new AC_LastMovementWorld[MAX_PLAYERS];
new AC_LastMovementState[MAX_PLAYERS];
new AC_MovementOverLimitSamples[MAX_PLAYERS];

new AC_LastVehicleId[MAX_PLAYERS];
new AC_VehicleOverLimitSamples[MAX_PLAYERS];

new AC_LastDamageTick[MAX_PLAYERS];
new AC_RapidDamageIntervals[MAX_PLAYERS];
new AC_LastCombatEvidenceTick[MAX_PLAYERS];
new AC_LastDamagedPlayer[MAX_PLAYERS];

new AC_NetworkPing[MAX_PLAYERS];
new AC_NetworkQualityTick[MAX_PLAYERS];
new Float:AC_NetworkPacketLoss[MAX_PLAYERS];
new bool:AC_NetworkPacketLossKnown[MAX_PLAYERS];

stock bool:AC_IsValidPlayerId(playerid)
{
    return playerid >= 0 && playerid < MAX_PLAYERS;
}

stock AC_ResetSampling(playerid)
{
    if (!AC_IsValidPlayerId(playerid))
        return 0;
    AC_LastUpdateTick[playerid] = 0;
    AC_LastMovementTick[playerid] = 0;
    AC_HasMovementSample[playerid] = false;
    AC_MovementOverLimitSamples[playerid] = 0;
    AC_LastVehicleId[playerid] = INVALID_VEHICLE_ID;
    AC_VehicleOverLimitSamples[playerid] = 0;
    AC_LastDamageTick[playerid] = 0;
    AC_RapidDamageIntervals[playerid] = 0;
    AC_LastCombatEvidenceTick[playerid] = 0;
    AC_LastDamagedPlayer[playerid] = INVALID_PLAYER_ID;
    return 1;
}

stock AC_ResetEvidence(playerid)
{
    if (!AC_IsValidPlayerId(playerid))
        return 0;
    AC_EvidenceHead[playerid] = 0;
    AC_EvidenceCount[playerid] = 0;

    for (new category; category < AC_CATEGORY_COUNT; category++)
        AC_CategoryLastAt[playerid][category] = 0;

    for (new slot; slot < AC_MAX_EVIDENCE; slot++)
    {
        AC_EvidenceTime[playerid][slot] = 0;
        AC_EvidenceCategory[playerid][slot] = -1;
        AC_EvidencePoints[playerid][slot] = 0;
        AC_EvidencePing[playerid][slot] = 0;
        AC_EvidenceMetric[playerid][slot] = 0.0;
        AC_EvidenceReason[playerid][slot][0] = '\0';
    }
    return 1;
}

stock AC_ResetPlayer(playerid)
{
    if (!AC_IsValidPlayerId(playerid))
        return 0;
    AC_PlayerLoaded[playerid] = false;
    AC_PlayerEnabled[playerid] = false;
    AC_AccountKey[playerid] = 0;
    AC_SuspicionScore[playerid] = 0;
    AC_StrikeCount[playerid] = 0;
    AC_LastScoreDecayAt[playerid] = 0;
    AC_LastStrikeDecayAt[playerid] = 0;
    AC_LastStrikeAt[playerid] = 0;
    AC_LastPersistAt[playerid] = 0;
    AC_Dirty[playerid] = false;
    AC_GraceStartedTick[playerid] = 0;
    AC_GraceDurationMs[playerid] = 0;
    AC_NetworkPing[playerid] = 0;
    AC_NetworkQualityTick[playerid] = 0;
    AC_NetworkPacketLoss[playerid] = 0.0;
    AC_NetworkPacketLossKnown[playerid] = false;

    AC_ResetEvidence(playerid);
    AC_ResetSampling(playerid);
    return 1;
}
