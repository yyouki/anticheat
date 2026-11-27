# open.mp staging harness

This is a disposable test gamemode for validating the anti-cheat integration contract in a real open.mp server. It is intentionally separate from production gamemodes and does not use a database, authentication provider, command framework, or third-party plugin.

## What it exercises

- Existing gamemode lifecycle callbacks forwarded into the anti-cheat core.
- A synthetic account load using `AC_BeginAccountLoad` and `AC_ApplyPersistentState`.
- The complete persistence callback contract, including the separate `score_decay_at`, `strike_decay_at`, and `last_strike_at` values.
- In-memory save and restore while the same staging server process remains running.
- Monitoring enable/disable, evidence inspection, and review-state reset.
- A server-owned teleport that notifies the framework before `SetPlayerPos`.
- Server-owned vehicle placement/removal with the corresponding vehicle-change notification.

The adapter keeps up to `MAX_PLAYERS` synthetic account records in RAM. All records are lost when the server process restarts. This is deliberate: the sample demonstrates the callback interface without selecting a database or suggesting that volatile storage is suitable for production.

## Get the compiled package

The repository CI workflow compiles `examples/staging.pwn` with the pinned Pawn compiler and publishes an artifact named `ac-staging-package` for successful workflow runs. Download that artifact from the workflow run's **Artifacts** section. The package contains:

- `gamemodes/ac-staging.amx`
- `config.json`
- this README

No local Pawn compiler is needed when using the CI artifact.

## Install on an isolated staging server

1. Obtain an open.mp server distribution from the [official server downloads](https://open.mp/downloads/server).
2. Extract it into a separate directory. Do not replace or reuse a production server directory.
3. Copy `gamemodes/ac-staging.amx` into the server's `gamemodes/` directory.
4. Copy this package's `config.json` to the server root, or merge its settings into an existing staging-only configuration. Preserve the host's normal settings where they differ.
5. Confirm the configured main script is `ac-staging 1` and that the server is not publicly announced. Keep the UDP port access limited to the people conducting the test.
6. Start the open.mp server using the hosting provider's normal server-start control or its documented launch procedure.
7. Connect with a supported game client and use the commands below.

The supplied config disables server-list announcement, query visibility, and RCON. Do not enable RCON for this harness. A hosting provider may require its own port, server-name, or startup configuration; adapt only the staging configuration, not the production server.

## Player test sequence

1. Join and spawn. Monitoring must remain off until the test account is loaded.
2. Run `/acstageauth 424242`. Use any positive synthetic account ID; do not use an actual account identifier.
3. Run `/acstageinfo` and confirm the account is loaded and monitoring is enabled.
4. Walk and drive normally while the server runs. This is for checking that valid gameplay and ordinary network variation do not create unexplained evidence.
5. Run `/acstageteleport`; the gamemode notifies the detector before the server-side position change. Confirm this legal transition does not create movement evidence.
6. Run `/acstagevehicle` and then `/acstageexitvehicle` to test server-owned vehicle placement and exit notifications.
7. Run `/acstagesave`, disconnect, reconnect, and authenticate again with the same synthetic account ID. Confirm the in-memory values load while the same server process is still running.
8. Run `/acstageevidence` and `/acstageclear` to inspect and clear the current review state.

Before the manual reconnect test, run `/acstagetest`. It performs in-server checks for stale session-token rejection, account-ID mismatch rejection, duplicate load rejection, restoration of the independent strike-cooldown timestamp, legitimate-action grace notification, persistence callback save, and state restoration after a simulated framework-session reset. It saves the currently authenticated synthetic account first and restores it after the test.

The self-test uses a reserved synthetic account ID range beginning at `2000000000`. Do not use that range for manually assigned test accounts. It simulates the framework disconnect/connect handlers while the real game client remains connected; it is not a network reconnect test. The separate manual disconnect/reconnect step below remains required.

Useful commands: `/acstagehelp`, `/acstageauth <accountid>`, `/acstageinfo`, `/acstagetest`, `/acstageevidence`, `/acstagetoggle`, `/acstagesave`, `/acstageclear`, `/acstageteleport`, `/acstagevehicle`, and `/acstageexitvehicle`.

## What this does not prove

The harness does not provide a durable database adapter, a client-side test bot, an exploit simulator, an automatic punishment system, or a production authentication flow. Compilation and a successful server start are not evidence that movement/vehicle thresholds are accurate. Actual runtime testing requires people to connect with the supported clients, representative legal server transitions, real network conditions, and a recorded false-positive review.

Do not use the volatile adapter as a production persistence implementation. Keep client memory scans and experimental combat cadence scoring disabled.
