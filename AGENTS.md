# Agent instructions: Neon

This repository uses Neon PostgreSQL for the NCAA 2026-27 data store.

## Required Neon workflow

- Before changing database configuration, read the current Neon documentation and the installed `neon-postgres` agent skill. Prefer official Neon documentation over remembered examples.
- Use the Neon CLI named `neon` (not the legacy `neonctl` name) when available.
- For a developer environment that has not been onboarded, ask the repository owner to run `npm install -g neon@latest` and then `neon init` from the repository directory. This performs the interactive Neon sign-in and configures the supported MCP/agent skill integrations. Do not claim onboarding is complete until authentication succeeds.
- If only the Neon skill is needed, use `neon skills -s neon-postgres`. To refresh an existing skill installation, use `neon skills update`.
- Use `neon link` to associate this checkout with the intended Neon project. Do not guess or silently select a project.
- Use `neon checkout <branch-name>` for isolated feature work and schema experiments. Keep production/default branch data unchanged unless the owner explicitly authorizes a production change.
- Use `neon diff` before applying or merging schema changes.
- Use `neon inspect db` for read-only database diagnostics before proposing fixes.
- Prefer project-scoped API keys for automation. Never request that a user paste an API key, database password, or full connection string into chat or commit secrets to Git.
- Never print credentials, write them into tracked files, or include them in logs. Use environment variables or the platform's secret manager.
- Treat database reads as the default. Before any destructive or production write (drop/truncate, destructive migration, reset, delete, bulk overwrite, or production import), explain the exact target and impact and obtain explicit user approval.
- Prefer Neon branches for experiments and migration validation. Do not reset or delete a branch unless the owner approves.
- The NCAA application is restricted to season key `2027` (2026-27). Never import historical seasons. Preserve source provenance and distinguish missing values from zero.
- For the Streamlit deployment, the application reads `DATABASE_URL` from Streamlit Secrets. GitHub Actions imports use the repository secret `NCAA_DATABASE_URL`. Never place either value in source control.

## Project-specific database contract

- PostgreSQL table: `ncaa_raw_rows`.
- The raw import is idempotent and keys rows by dataset, artifact SHA-256, and source row number.
- Do not assume raw JSONB rows are normalized analytics tables.
- Do not claim the database contains NCAA data until a read-only query confirms imported rows.
- Keep the free-tier storage/compute limits in mind; inspect Neon usage before expanding ingestion.
