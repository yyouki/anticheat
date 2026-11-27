#if defined _AC_CONFIG_INCLUDED
    #endinput
#endif
#define _AC_CONFIG_INCLUDED

#define AC_VERSION                          "0.1.0"
#define AC_MAX_EVIDENCE                     (8)
#define AC_EVIDENCE_REASON_LENGTH           (48)
#define AC_CATEGORY_COUNT                   (5)

#define AC_CATEGORY_MOVEMENT                (0)
#define AC_CATEGORY_VEHICLE                 (1)
#define AC_CATEGORY_COMBAT                  (2)
#define AC_CATEGORY_STATE                   (3)
#define AC_CATEGORY_INTEGRITY               (4)

#define AC_EVIDENCE_WINDOW_SECONDS           (120)
#define AC_CATEGORY_COOLDOWN_SECONDS         (8)
#define AC_SCORE_STRIKE_THRESHOLD            (65)
#define AC_SCORE_STRIKE_REDUCTION            (35)
#define AC_STRIKE_COOLDOWN_SECONDS           (300)
#define AC_SCORE_DECAY_SECONDS               (300)
#define AC_STRIKE_DECAY_SECONDS              (21600)
#define AC_PERSIST_INTERVAL_SECONDS          (30)

#define AC_SAMPLE_INTERVAL_MS                (500)
#define AC_MAX_SAMPLE_GAP_MS                 (1750)
#define AC_DEFAULT_GRACE_MS                  (4000)

#define AC_MOVEMENT_MAX_PING                 (450)
#define AC_MOVEMENT_BASE_SPEED               (22.0)
#define AC_MOVEMENT_PING_TOLERANCE           (0.01)
#define AC_MOVEMENT_MAX_PING_TOLERANCE       (5.0)
#define AC_MOVEMENT_REQUIRED_SAMPLES         (3)

#define AC_VEHICLE_MAX_PING                  (400)
#define AC_VEHICLE_MAX_SPEED_KMH             (385.0)
#define AC_VEHICLE_PING_TOLERANCE            (0.02)
#define AC_VEHICLE_MAX_PING_TOLERANCE        (10.0)
#define AC_VEHICLE_REQUIRED_SAMPLES          (3)
#define AC_VEHICLE_SPEED_FACTOR              (250.66667)

// Generic damage callback timing is not reliable enough for all clients.
// Keep disabled until a server-specific trace corpus validates the heuristic.
#if !defined AC_ENABLE_COMBAT_CADENCE
    #define AC_ENABLE_COMBAT_CADENCE         (0)
#endif
#define AC_COMBAT_MAX_PING                   (160)
#define AC_COMBAT_MIN_INTERVAL_MS            (30)
#define AC_COMBAT_REQUIRED_FAST_INTERVALS    (4)
#define AC_COMBAT_EVIDENCE_COOLDOWN_MS       (30000)

// Client memory checks are intentionally disabled. No universal offsets exist.
#if !defined AC_ENABLE_CLIENT_MEMORY_CHECKS
    #define AC_ENABLE_CLIENT_MEMORY_CHECKS   (0)
#endif

// A single family cannot trigger a strike. At least two independent families
// must report inside AC_EVIDENCE_WINDOW_SECONDS.
