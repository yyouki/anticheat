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

## Change management

- Start from the latest `main` on a focused branch. Keep unrelated work out of the same PR.
- Update tests and documentation with behavior or callback/API changes.
- Never rewrite expected fixture output only to silence a regression.
- Update `docs/PROJECT_CONTEXT.md` with meaningful changes to architecture, API contracts, merged PRs, CI state, or next steps.
- Prefer small, reviewable commits and a draft PR while CI or runtime validation is incomplete.
