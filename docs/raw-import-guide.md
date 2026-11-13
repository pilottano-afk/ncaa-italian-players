# Conservative raw-data import (NCAA 2026-27)

The importer is the first database step after staging and quality audit. It stores the original provider rows as JSONB and deliberately does **not** infer player nationality or create relational foreign keys.

## What it checks before writing

- `manifest.json` must identify season `2027` and explicitly disable historical data.
- Every dataset must have a validated, non-null `season` column containing only `2027`.
- `quality-audit.json` must exist, identify season `2027`, and report row counts matching the manifest.
- All Parquet files are preflighted before the first database write: file signature, row count, season column, null season rows and distinct season values.
- Every imported row is checked again; a historical or null season value stops the import.
- The import runs in one transaction per dataset; the artifact hash and row number make retries idempotent.
- PostgreSQL is required. SQLite is not supported for this operation.

## Run locally

1. Put the contents of the successful GitHub Actions artifact ZIP in `data/staging/2027/`. The directory must contain `manifest.json`, `quality-audit.json`, and the 11 `ncaa_mbb_*_2027.parquet` files.
2. Start PostgreSQL from the repository root:

   ```bash
   docker compose up -d db
   ```

3. Install the project in the same Python environment:

   ```bash
   python -m pip install -e .
   ```

4. Set the local development database URL and import:

   ```bash
   export DATABASE_URL='postgresql+psycopg://ncaa:ncaa@localhost:5432/ncaa_players'
   ncaa-import-raw --input data/staging/2027
   ```

The importer writes to `ncaa_raw_rows`. It uses the SHA-256 hash of each Parquet file plus its source row number as an idempotency key. Re-importing the exact same artifact will not duplicate rows. A newly generated Parquet file has a new hash and is retained as a separate source snapshot.

## Verify the result

Open a PostgreSQL shell:

```bash
docker compose exec db psql -U ncaa -d ncaa_players
```

Then run:

```sql
SELECT dataset, season, COUNT(*) AS rows
FROM ncaa_raw_rows
GROUP BY dataset, season
ORDER BY dataset;
```

To inspect a source record without losing the original field names:

```sql
SELECT dataset, source_file, source_row_number, payload
FROM ncaa_raw_rows
WHERE dataset = 'schedule'
ORDER BY source_row_number
LIMIT 3;
```

## What this step does not do

- It does not create the final normalized player, team, game, lineup, possession or shot tables.
- It does not decide whether a player is Italian.
- It does not calculate advanced statistics.
- It does not claim that the 2026-27 season is complete.
- It does not run automatically in GitHub Actions, where there is no persistent project database configured.

The GitHub Actions test workflow includes a PostgreSQL service and an end-to-end idempotency test for the importer. This verifies the import path against a real PostgreSQL engine without using or changing your personal database.

This separation preserves the source data while allowing the next phase to build and test normalized analytical views against real records.
