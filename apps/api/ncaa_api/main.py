from __future__ import annotations

import os

from fastapi import FastAPI, HTTPException, Query
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

from ncaa_api.providers.cbbd import CollegeBasketballDataClient
from ncaa_api.providers.sportsdataverse import DATASETS
from ncaa_api.sources import SOURCE_CATALOG, SourceHealth

app = FastAPI(
    title="NCAA Italian Players API",
    version="0.3.0",
    description="Real-data NCAA 2026-27 analytics API. No historical seasons or synthetic stats.",
)


def _database_summary() -> dict[str, object]:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        return {"status": "not_configured", "season": 2027, "datasets": [], "rows_total": 0}
    if database_url.startswith("postgresql://"):
        database_url = "postgresql+psycopg://" + database_url.removeprefix("postgresql://")
    engine = create_engine(database_url, pool_pre_ping=True)
    try:
        with engine.connect() as connection:
            rows = connection.execute(text("""
                SELECT dataset, COUNT(*) AS rows,
                       COUNT(DISTINCT artifact_sha256) AS artifacts,
                       MAX(imported_at) AS last_imported_at
                FROM ncaa_raw_rows
                WHERE season = 2027
                GROUP BY dataset
                ORDER BY dataset
            """)).mappings().all()
        datasets = [
            {
                "dataset": row["dataset"],
                "rows": int(row["rows"]),
                "artifacts": int(row["artifacts"]),
                "last_imported_at": row["last_imported_at"].isoformat() if row["last_imported_at"] else None,
            }
            for row in rows
        ]
        return {
            "status": "connected" if datasets else "connected_empty",
            "season": 2027,
            "datasets": datasets,
            "rows_total": sum(item["rows"] for item in datasets),
        }
    except SQLAlchemyError as exc:
        return {
            "status": "table_not_ready" if "ncaa_raw_rows" in str(exc) else "unavailable",
            "season": 2027,
            "datasets": [],
            "rows_total": 0,
            "message": str(exc).splitlines()[0][:240],
        }
    finally:
        engine.dispose()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "season": "2027", "season_label": "2026-27"}


@app.get("/api/v1/database/summary")
def database_summary() -> dict[str, object]:
    return _database_summary()


@app.get("/api/v1/database/datasets")
def database_datasets() -> dict[str, object]:
    summary = _database_summary()
    return {
        "season": 2027,
        "available_datasets": sorted(DATASETS),
        "imported_datasets": summary.get("datasets", []),
        "status": summary["status"],
    }


@app.get("/api/v1/raw/{dataset}")
def raw_dataset(
    dataset: str,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> dict[str, object]:
    """Browse original imported records without guessing provider field semantics."""
    if dataset not in DATASETS:
        raise HTTPException(status_code=404, detail="Dataset NCAA non riconosciuto.")
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise HTTPException(status_code=503, detail="Database non configurato.")
    if database_url.startswith("postgresql://"):
        database_url = "postgresql+psycopg://" + database_url.removeprefix("postgresql://")
    engine = create_engine(database_url, pool_pre_ping=True)
    try:
        with engine.connect() as connection:
            total = connection.execute(
                text("SELECT COUNT(*) FROM ncaa_raw_rows WHERE season = 2027 AND dataset = :dataset"),
                {"dataset": dataset},
            ).scalar_one()
            rows = connection.execute(
                text("""
                    SELECT source_file, artifact_sha256, source_row_number, imported_at, payload
                    FROM ncaa_raw_rows
                    WHERE season = 2027 AND dataset = :dataset
                    ORDER BY source_row_number
                    LIMIT :limit OFFSET :offset
                """),
                {"dataset": dataset, "limit": limit, "offset": offset},
            ).mappings().all()
        return {
            "season": 2027,
            "dataset": dataset,
            "total": int(total),
            "limit": limit,
            "offset": offset,
            "records": [
                {
                    "source_file": row["source_file"],
                    "artifact_sha256": row["artifact_sha256"],
                    "source_row_number": row["source_row_number"],
                    "imported_at": row["imported_at"].isoformat(),
                    "payload": row["payload"],
                }
                for row in rows
            ],
        }
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail="Tabella dati grezzi non disponibile: " + str(exc).splitlines()[0][:180]) from exc
    finally:
        engine.dispose()


@app.get("/api/v1/coverage")
def coverage() -> dict[str, object]:
    cbbd = CollegeBasketballDataClient()
    source_health = [
        SourceHealth.make(
            "sportsdataverse",
            "SportsDataverse NCAA MBB",
            "not_checked",
            message="Release assets were verified in the repository; this API process has not yet downloaded or validated their contents.",
            documentation_url="https://github.com/sportsdataverse/ncaa-mbb-hoops-data",
        ).as_dict(),
        SourceHealth.make(
            "collegebasketballdata",
            "CollegeBasketballData.com",
            "configured" if cbbd.configured else "not_configured",
            message=(
                "API key not configured; no live request has been made."
                if not cbbd.configured
                else "API key is present; no live dataset request has been made yet."
            ),
            documentation_url="https://api.collegebasketballdata.com/data-availability",
        ).as_dict(),
    ]
    database = _database_summary()
    return {
        "season": 2027,
        "season_label": "2026-27",
        "historical_data_enabled": False,
        "sources": SOURCE_CATALOG,
        "source_health": source_health,
        "database": database,
        "status": database["status"],
        "note": "Counts reflect raw rows actually present in PostgreSQL; no analytics are inferred from unimported staging files.",
    }
