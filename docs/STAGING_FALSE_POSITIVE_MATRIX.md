# Interactive staging and false-positive evaluation

This matrix is an operator worksheet for real, isolated staging runs. It is not a synthetic CI fixture and does not claim that any scenario has already been executed.

## Run isolation and identity

Use a private staging server with announcement, query visibility and RCON disabled. Use only synthetic test accounts. Do not use production players, production credentials, real account IDs, player IDs, IP addresses, device identifiers, or private chat in the review record.

Use one review JSON file per client build and network profile. Record the exact main commit used by the server and the SHA-256 digest of the downloaded staging package. Keep the raw server console log local: it may contain host connection metadata not present in the structured AC-STAGE-EVENT records.

The client_platform field is a broad platform label (android, windows, linux, macos, or other). client_build is a short release/build label only; do not enter device model serials, IMEI, account names or other unique device identifiers. network_profile identifies the controlled test condition for this run: stable, high_ping, jitter, packet_loss, or low_fps. Use a separate record for each condition. Do not label a run with a network condition that was not actually observed.

## Required scenario matrix

The machine-readable source of scenario IDs and expected outcomes is tools/anticheat/staging_review_scenarios.json. Each review record contains one observation per scenario, or a subset when a run is intentionally partial. Missing scenarios are reported as incomplete.

| Scenario ID | Exercise | Expected benign result |
| --- | --- | --- |
| walk_idle | Stand still, walk and sprint normally. | No movement evidence. |
| jump_fall_land | Jump, fall and land normally. | No movement evidence. |
| admin_teleport | Execute the staging server-authorized teleport. | No movement evidence after the host transition notification. |
| spawn_death_respawn | Spawn, die and respawn using normal game flow. | No evidence caused solely by lifecycle transitions. |
| interior_roundtrip | Enter and leave interior 17 using the staging command. | No evidence in either direction. |
| virtual_world_roundtrip | Enter and leave virtual world 9000 using the staging command. | No evidence in either direction. |
| vehicle_enter_drive_exit | Enter, drive and exit the staging vehicle. | No vehicle evidence for ordinary driver activity. |
| vehicle_switch_collision | Switch vehicles and observe ordinary collision impulses. | No evidence for representative legal vehicle activity. |
| spectate_roundtrip | Spectate the second connected client and restore the original context. | No evidence; record secondary_client_connected=true. |
| disconnect_reconnect | Perform an actual client disconnect and reconnect, then authenticate the same synthetic account. | No stale-session evidence. The simulated /acstagetest reset is not a substitute. |
| network_condition_sample | Repeat ordinary movement and vehicle activity under the selected network profile. | No false evidence caused solely by the declared network condition. |

The full /acstagelogbegin to /acstagelogend acceptance capture remains a separate transition-sequence check. A staging report status=pass means only that its structured records meet the expected log contract; it does not replace the scenario observations above.

## Recording observations

1. Copy docs/templates/staging-review-template.json to a new local file for each client build and network profile.
2. Fill server_commit with the exact 40-character commit SHA and staging_artifact_sha256 with the artifact digest. Fill client_build with a non-identifying build label and started_at with an ISO-8601 timestamp including timezone.
3. Set each scenario result to:
   - clean: the scenario was executed and no evidence/review marker was observed.
   - evidence: evidence was observed. Name every evidence category and choose a human review decision.
   - blocked: the scenario could not be executed. Use one controlled block_reason.
   - not_run: the scenario has not been attempted.
4. For an evidence result, choose pending, confirmed_false_positive, rejected_false_positive, or inconclusive. Do not automatically classify evidence as a false positive or dismiss it. Preserve the evidence for human review.
5. For spectate_roundtrip, set secondary_client_connected=true only when the second test client was actually connected for that scenario.
6. Validate the local record:

   ```sh
   python3 tools/anticheat/staging_review.py --record /path/to/staging-review.json
   ```

7. Keep the review JSON and raw logs private unless they have been checked for accidental identifiers. Share only the redacted summary when reporting results.

## Binding a review to its staging capture

The schema-v2 review record requires `environment.capture_sha256`. After saving the completed local console log, run:

```sh
python3 tools/anticheat/staging_review_capture.py --record /path/to/staging-review.json --capture-log /path/to/staging-console.log --write-digest
```

This validates the structured event sequence and writes the SHA-256 digest of the exact raw file bytes into the review record. Repeat without `--write-digest` to verify the binding later. The command rejects symlink inputs and raw captures larger than 32 MiB. It does not upload either file, authenticate log origin, or prove that the scenario observations were performed.

The batch tool rejects a repeated `capture_sha256` across distinct run IDs, preventing accidental reuse of one capture as multiple independent runs. Keep the raw log and review record private.

## Collecting vehicle telemetry observations

During each bounded acceptance capture, the staging gamemode also writes `[AC-STAGE-VEHICLE]` records for the primary client while it is driving. Samples are limited to two per second and 3,600 per capture (about 30 minutes at the full sampling rate); after the cap, collection stops and emits one notice. Each sample contains an approved road-car model ID, quantized server-side speed, ping, and a fresh host-supplied packet-loss value when one exists. Unknown packet loss is recorded as `-1`. The stock staging gamemode does not configure a packet-loss provider, so the field normally remains unknown unless a host integration supplies a fresh measurement through `AC_SetNetworkQuality`. Player IDs, account IDs, vehicle IDs, and coordinates are not written.

Use one vehicle model per complete acceptance capture because the transition report intentionally requires one vehicle-enter/exit pair. The staging command accepts `/acstagevehicle <modelid>`; it defaults to model 411. Approved model IDs are:

`400, 401, 402, 404, 405, 410, 411, 415, 419, 421, 426, 429, 436, 439, 445, 451, 458, 477, 489, 496, 506, 517, 518, 526, 527, 533, 541, 546, 547, 550, 555, 560, 562, 565, 566, 567, 575, 576, 580, 585, 587, 589, 602, 603`.

Only combine captures from the same server commit, client build, and network profile. Keep different client or network profiles in separate reports so their distributions are not blended.

The report accepts individual source logs up to 32 MiB each, a combined 64 MiB total, and 100,000 observations. It rejects symlinks and unsupported model IDs.

For an exploratory summary, logs can be read without review records. Such output has \`provenance.binding_status=not_provided\` and must not be treated as an evidence-bound run.

For a bound summary, first fill the schema-v2 review JSON for each capture and bind it to the exact raw file:

\`\`\`sh
python3 tools/anticheat/staging_review_capture.py --record /path/to/model-411-review.json --capture-log /path/to/model-411-console.log --write-digest
\`\`\`

Pass each log and its matching record in the same order:

\`\`\`sh
python3 tools/anticheat/vehicle_trace_report.py \\
  --log /path/to/model-411-console.log --record /path/to/model-411-review.json \\
  --log /path/to/model-560-console.log --record /path/to/model-560-review.json --json
\`\`\`

Bound mode checks the exact capture SHA-256, full staging transition contract, and the review record schema. It requires a clean \`vehicle_enter_drive_exit\` review observation and distinct run IDs and capture digests. It rejects captures with no vehicle observations, more than one vehicle model in a file, or mismatched server commit, staging artifact, open.mp version, client platform/build, or network profile. Limits are 500 captures, 64 MiB combined logs, 8 MiB combined review records, and 100,000 telemetry samples.

A verified binding links the report to the precise files and operator-entered metadata. It does not authenticate log origin or independently verify scenario execution. The report always leaves detector accuracy, safe speed envelope, and production readiness unverified. Percentiles are observations, not safe speed limits. Keep raw logs and review records local.

## Interpreting the validator output

record_status=valid means only that the review record has the required fields and internally consistent result labels. scenario_execution_complete means every scenario in the manifest has a clean or evidence observation. evidence_review_complete means there are no pending or inconclusive evidence decisions. A confirmed false positive remains visible in confirmed_false_positive_count and the evaluation state.

The validator deliberately never certifies false_positive_free_certified, independently_verified, or production_ready. These remain false even when every scenario is marked clean. The tool cannot verify that a human actually executed the test, authenticate a server log, estimate a statistically meaningful false-positive rate, or prove detector accuracy.

## Evaluation rules

Do not change detector thresholds based on one run or synthetic fixtures. Compare repeated runs across supported client builds and network profiles. Investigate each evidence record with its category, timestamp/order from the local log, relevant ping/packet-loss context, and the server-side action that preceded it. Change a detector only after the cause is understood and a regression test shows that the fix does not suppress unrelated evidence.

The sample persistence adapter is RAM-only. A server process restart loses its saved records; this harness does not validate durable production persistence. Never run this worksheet against a production gamemode or public server.


## Comparing multiple review runs

Keep each completed review JSON file in a private local directory. Use a distinct, non-identifying `run_id` for every run. The batch aggregator validates every file before producing a combined report:

```sh
python3 tools/anticheat/staging_review_batch.py --records-dir /path/to/private-review-records
```

The output groups runs by the exact server commit, staging artifact digest, open.mp version, client platform/build label, and network profile. Each group contains total result counts and per-scenario counts, so a scenario that repeatedly produces evidence is visible instead of being hidden in an overall total.

The command rejects a batch containing an invalid record or duplicate run ID; it does not silently produce a partial-success summary. It reads only top-level, non-symlink JSON files, limits a batch to 500 records, and rejects individual files larger than 1 MiB. Keep the directory local: even though the schema excludes player/account/device identifiers, run metadata and test outcomes may still be operationally sensitive.

Counts are observations, not false-positive rates. Runs may not be independent, durations may differ, and the validator cannot verify execution. The summary never certifies false-positive-free behavior, independent verification, or production readiness.
