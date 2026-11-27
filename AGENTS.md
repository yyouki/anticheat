# Contributor and Coding-Agent Instructions

Before changing code, read `docs/PROJECT_CONTEXT.md`, `README.md`, `docs/ROADMAP.md`, and `docs/VALIDATION.md`. Then inspect the relevant implementation, tests, and workflow files. Treat `docs/PROJECT_CONTEXT.md` as the durable handoff record, not as a substitute for verifying current source and CI.

## Repository boundaries

- Keep this project independent of any specific roleplay gamemode, including Pylance Roleplay.
- Do not assume an account table, database schema, SQL plugin, command processor, hosting provider, or authentication flow.
- Do not add unrelated services, dependencies, or schema migrations to the framework core.
- Write source comments and repository documentation in English.

## Security and behavior invariants

- Preserve the evidence-first policy. A strike is a review marker, never an automatic punishment.
- Do not add automatic kicks, bans, freezes, rewinds, or other player sanctions.
- Keep client memory scanning and combat cadence scoring disabled by default unless a separate, evidence-backed design review changes that policy.
- Treat client synchronization as untrusted input and legal server-side transitions as explicit adapter context.
- Prefer conservative suppression/reset behavior when network quality or sample validity is uncertain.
- Keep `score_decay_at`, `strike_decay_at`, and `last_strike_at` separate in all persistence adapters and documentation.
- Use synthetic, privacy-safe fixtures only.

## Validation and reporting

- Run Python unit tests and replay fixtures when touching the reference model, fixture schema, thresholds, or detector contract.
- Run the static audit and both Pawn smoke compile modes for core/include changes.
- Inspect failed workflow job logs. Do not claim a skipped or failed step passed.
- State clearly whether a check is compile-only, synthetic reference replay, or actual runtime validation.
- Do not describe the framework as production-ready until every release gate in `docs/VALIDATION.md` has evidence.

## Change management and merge workflow

- Start from the latest `main` on a focused branch for substantive changes. Small documentation-only corrections may be made directly on `main` when safe.
- Update tests and documentation with behavior or callback/API changes.
- Never rewrite expected fixture output only to silence a regression.
- Update `docs/PROJECT_CONTEXT.md` with meaningful changes to architecture, API contracts, merged PRs, CI state, or project preferences.
- The repository owner prefers a low-friction merge flow and does not want routine manual line-by-line PR review as a required step.
- Perform the implementation review and inspect the diff yourself. When CI is green and no unresolved blocker is known, present a concise summary and test results rather than asking the owner to manually review every change.
- Mark PRs ready when their relevant CI checks pass. Do not merge on the owner's behalf unless explicitly asked.
- If CI fails, security-sensitive behavior changes, or a specific unresolved risk exists, explain that concrete blocker.

