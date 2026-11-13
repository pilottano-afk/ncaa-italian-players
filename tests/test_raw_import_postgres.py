import json
import os
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from sqlalchemy import create_engine, text

from ncaa_api.raw_import import import_staged_raw


@pytest.mark.skipif(not os.environ.get("DATABASE_URL"), reason="PostgreSQL integration URL not configured")
def test_postgres_raw_import_is_idempotent(tmp_path: Path) -> None:
    database_url = os.environ["DATABASE_URL"]
    parquet_path = tmp_path / "ncaa_mbb_schedule_2027.parquet"
    pq.write_table(
        pa.table({"contest_id": ["game-1", "game-2"], "season": [2027, 2027]}),
        parquet_path,
    )
    manifest = {
        "season": 2027,
        "historical_data_enabled": False,
        "database_imported": False,
        "datasets": [{
            "dataset": "schedule",
            "rows": 2,
            "season_validation": "validated",
            "season_null_rows": 0,
            "distinct_season_values": [2027],
        }],
    }
    audit = {
        "season": 2027,
        "database_imported": False,
        "datasets": {"schedule": {"rows": 2}},
    }
    (tmp_path / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    (tmp_path / "quality-audit.json").write_text(json.dumps(audit), encoding="utf-8")

    engine = create_engine(database_url)
    try:
        first = import_staged_raw(tmp_path, database_url)
        second = import_staged_raw(tmp_path, database_url)
        assert first["inserted_rows_total"] == 2
        assert first["already_present_rows_total"] == 0
        assert second["inserted_rows_total"] == 0
        assert second["already_present_rows_total"] == 2

        with engine.connect() as connection:
            count = connection.execute(
                text("""
                    SELECT COUNT(*) FROM ncaa_raw_rows
                    WHERE dataset = 'schedule'
                      AND source_file = 'ncaa_mbb_schedule_2027.parquet'
                """)
            ).scalar_one()
        assert count == 2
    finally:
        with engine.begin() as connection:
            table_exists = connection.execute(
                text("SELECT to_regclass('public.ncaa_raw_rows')")
            ).scalar_one()
            if table_exists:
                connection.execute(
                    text("""
                        DELETE FROM ncaa_raw_rows
                        WHERE dataset = 'schedule'
                          AND source_file = 'ncaa_mbb_schedule_2027.parquet'
                    """)
                )
        engine.dispose()
