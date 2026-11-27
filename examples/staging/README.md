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
- A real interior transition using interior 17, including a return to the saved position.
- A virtual-world transition to reserved staging world 9000 and a return to the saved world.
- Spectating another connected player, including alignment to the target's interior/world and restoration after spectating ends.
- Privacy-safe structured acceptance events for teleport, vehicle, interior, virtual-world, spectating, evidence, and review-marker observations.
- Supplemental server-side vehicle telemetry observations while the primary test client is driving: approved road-car model, quantized speed, ping, and fresh host-supplied packet loss when available. Records are capped at two samples per second and exclude player, account, vehicle, and position identifiers.
- An offline Python report checker that rejects incomplete or failed transition sequences and any evidence/review marker during the capture window.

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

1. Join with the primary test client and spawn. Monitoring must remain off until the test account is loaded.
2. Run `/acstageauth 424242`. Use a positive synthetic account ID; never use an actual account identifier.
3. Run `/acstageinfo` and confirm that the account is loaded and monitoring is enabled.
4. Connect a second test client. Keep both clients on foot in exterior interior 0 and the same virtual world. The second client should remain connected and stationary as the spectating target.
5. Run `/acstagetest` before beginning the capture. It checks stale session-token rejection, account-ID mismatch rejection, duplicate load rejection, timestamp restoration, grace notifications, persistence save, and simulated framework-session restoration. It exercises framework reset handlers while the real game client remains connected; it does not disconnect the real client.
6. On the primary client, run `/acstagelogbegin`. This starts one bounded acceptance window. Do not begin a second capture until the first one has ended.
7. During the capture, walk normally, then run `/acstageteleport`.
8. Select one approved vehicle model for this capture with `/acstagevehicle <modelid>` (or omit the argument for model 411). Drive normally at varied speeds for at least 30 seconds, then run `/acstageexitvehicle`. Use one vehicle model per acceptance capture because the acceptance parser expects exactly one vehicle-enter/exit sequence. Repeat the complete capture for another model rather than spawning multiple models in the same run.
9. Run `/acstageinterior` twice to enter and leave the 24/7 interior (ID 17). Then run `/acstageworld` twice to enter and leave reserved virtual world 9000.
10. Run `/acstagespectate <targetid>` on the primary client, then `/acstageunspectate`. The target is logged only as the pseudonymous role `secondary`; the report never needs either client's player ID. The harness restores the spectator's previous position/context after spectating ends.
11. On the primary client, run `/acstagelogend`. Copy the server console log to a local text file. The structured `[AC-STAGE-EVENT]` records contain only the fixed role labels `primary` and `secondary`, transition values, and detector category counters. Supplemental `[AC-STAGE-VEHICLE]` records contain only the fixed `primary` role, model ID, quantized speed, ping, and optional packet-loss measurement. Neither record type includes player IDs, account IDs, vehicle IDs, coordinates, IP addresses, or session tokens.
The raw server console log may contain unrelated host/server connection metadata. Keep it local, do not commit or publicly upload it, and share only the redacted report summary if results need to be discussed.

12. Run the offline transition report checker from the repository root:

    ```sh
    python3 tools/anticheat/staging_report.py --log /path/to/staging-console.log
    ```

    For automation, append `--json` to print a machine-readable summary:

    ```sh
    python3 tools/anticheat/staging_report.py --log /path/to/staging-console.log --json
    ```

    The JSON includes a versioned report schema, pass/fail status, event counts, evidence/review counts, and errors. Its `runtime_validation` fields deliberately remain false: this parser does not verify a connected client's behavior, authenticate the log's origin, or determine production readiness. A JSON `status: pass` means only that the supplied structured records satisfy the expected log contract.

    The parser also rejects malformed or duplicate fields, negative counters, unknown evidence categories, non-pseudonymous spectate targets, and event-specific records missing required transition fields. These checks validate the structured record contract; they do not authenticate who produced the log.

13. For a descriptive per-model speed and network summary, run the supplemental local tool. Repeat `--log` for each separate model capture:

    ```sh
    python3 tools/anticheat/vehicle_trace_report.py \\
      --log /path/to/model-411-console.log \\
      --log /path/to/model-560-console.log
    ```

    The summary reports sample count and min/p50/p95/max speed and ping for each model, plus packet-loss statistics where available. It ignores ordinary transition events and reads only `[AC-STAGE-VEHICLE]` records. The summary is descriptive only: percentiles are not safe speed limits, and they do not prove a detector false positive or false negative. Keep source logs local.

The report must show `PASS`. It requires the complete teleport, vehicle, interior callback, world, and spectating event sequence. Any evidence, review marker, missing callback, failed restoration, capture abort, or incomplete capture makes the report fail. The parser ignores ordinary console lines and only evaluates the structured records inside the capture window.
14. Outside the capture, run `/acstageevidence` and `/acstageclear` to inspect and clear the current review state. Then run `/acstagesave`, disconnect, reconnect, and authenticate again with the same synthetic account ID. This persistence test works only while the same server process remains running.

Useful commands: `/acstagehelp`, `/acstageauth <accountid>`, `/acstageinfo`, `/acstagetest`, `/acstageevidence`, `/acstagetoggle`, `/acstagesave`, `/acstageclear`, `/acstageteleport`, `/acstagevehicle [modelid]`, `/acstageexitvehicle`, `/acstageinterior`, `/acstageworld`, `/acstagespectate <playerid>`, `/acstageunspectate`, `/acstagelogbegin`, and `/acstagelogend`.

The `/acstagetest` command reserves synthetic account IDs beginning at `2000000000` for its internal persistence checks. Do not assign that range to manually selected staging test accounts.

## What this does not prove

The harness does not provide a durable database adapter, a client-side test bot, an exploit simulator, an automatic punishment system, or a production authentication flow. Vehicle telemetry is sampled from server-side state for observation only; it is not an additional detector input or a model-specific threshold. The offline acceptance report verifies that expected staging callbacks and commands were observed without evidence or review markers during one bounded test window. It is not an exploit simulator and does not establish movement/vehicle threshold accuracy, mobile/desktop false-positive rates, real reconnect behavior, production performance, or release readiness. Actual runtime testing still requires supported connected clients and representative network conditions.

Do not use the volatile adapter as a production persistence implementation. Keep client memory scans and experimental combat cadence scoring disabled.


## Per-client false-positive review

For repeatable observations, use the interactive staging and false-positive matrix in docs/STAGING_FALSE_POSITIVE_MATRIX.md. It defines the required benign scenarios and a privacy-safe review record for each client build/network profile.

The review record template is docs/templates/staging-review-template.json. Copy it locally, fill in the server commit, staging artifact SHA-256, client build label, timezone-aware start time, and scenario outcomes. Validate it with:

\`\`\`sh
python3 tools/anticheat/staging_review.py --record /path/to/staging-review.json
\`\`\`

The validator checks record structure and whether scenario/evidence reviews are complete. It cannot prove that the scenarios were actually executed or that a run is false-positive-free. Its output always leaves independent verification and production readiness false. Keep review records and raw logs local and remove any accidental identifiers before sharing a summary.

The review template uses schema version 2. Bind the review record to the exact raw capture file with:

```sh
python3 tools/anticheat/staging_review_capture.py --record /path/to/staging-review.json --capture-log /path/to/staging-console.log --write-digest
```

This command checks the staging log contract, computes SHA-256 over the exact raw file bytes, upgrades a schema-v1 record to schema v2 when explicitly requested, and writes the digest into `environment.capture_sha256`. Run it again without `--write-digest` to verify the binding later. It rejects symlinks and capture files larger than 32 MiB. It prints no raw log contents or local file paths. This binds the review to one exact file and checks its structure; it does not authenticate who produced the log or prove that a human executed the scenarios.


For repeated client/build/network runs, use the batch summary tool after individually validating and saving each review JSON in a private directory:

```sh
python3 tools/anticheat/staging_review_batch.py --records-dir /path/to/private-review-records
```

It groups by exact build/environment metadata and includes per-scenario counts. It rejects invalid or duplicate run records and reports counts only; it does not calculate false-positive rates or certify runtime behavior.
