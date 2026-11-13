"""Conservative PostgreSQL raw-row import for the NCAA 2026-27 staging files.

This layer preserves provider rows without imposing unverified relational keys.
It is intentionally separate from normalized analytics tables.
"""
from __future__ import annotations

import base64
import hashlib
import json
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Iterable

import pyarrow.parquet as pq
from sqlalchemy import create_engine, text

from ncaa_api.season import CURRENT_SEASON, CURRENT_SEASON_LABEL, require_current_season
from ncaa_api.providers.sportsdataverse import DATASETS, SportsDataverseClient


TABLE_DDL = """
CREATE TABLE IF NOT EXISTS ncaa_raw_rows (
    season INTEGER NOT NULL CHECK (season = 2027),
    dataset TEXT NOT NULL,
    source_file TEXT NOT NULL,
    artifact_sha256 TEXT NOT NULL,
    source_row_number BIGINT NOT NULL,
    payload JSONB NOT NULL,
    imported_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (dataset, artifact_sha256, source_row_number)
)
"""

INSERT_SQL = text("""
INSERT INTO ncaa_raw_rows
    (season, dataset, source_file, artifact_sha256, source_row_number, payload)
VALUES
    (:season, :dataset, :source_file, :artifact_sha256, :source_row_number,
     CAST(:payload AS JSONB))
ON CONFLICT (dataset, artifact_sha256, source_row_number) DO NOTHING
""")


def _json_value(value: Any) -> Any:
    """Convert Arrow/Python values into loss-minimizing JSON-compatible values."""
    if value is None or isinstance(value, (str, int, bool)):
        return value
    if isinstance(value, float):
        if value != value:
            return {"__type__": "non_finite_float", "value": "NaN"}
        if value in (float("inf"), float("-inf")):
            return {"__type__": "non_finite_float", "value": "Infinity" if value > 0 else "-Infinity"}
        return value
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, bytes):
        return {"__type__": "bytes_base64", "value": base64.b64encode(value).decode("ascii")}
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    # Arrow extension values should normally arrive as Python primitives from to_pylist().
    # Keep an explicit representation rather than silently dropping an unfamiliar value.
    if hasattr(value, "as_py"):
        return _json_value(value.as_py())
    raise TypeError(f"Unsupported value for raw JSON preservation: {type(value).__name__}")


def _normalize_database_url(database_url: str) -> str:
    """Select the installed psycopg 3 SQLAlchemy dialect explicitly."""
    if database_url.startswith("postgresql://"):
        database_url = "postgresql+psycopg://" + database_url.removeprefix("postgresql://")
    if not database_url.startswith("postgresql+psycopg://"):
        raise ValueError("Raw import currently requires PostgreSQL with psycopg 3.")
    return database_url


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _validate_manifest(folder: Path) -> dict[str, Any]:
    manifest_path = folder / "manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"Required staging manifest not found: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if int(manifest.get("season", -1)) != CURRENT_SEASON:
        raise ValueError(f"Manifest must be for NCAA season {CURRENT_SEASON_LABEL}.")
    if manifest.get("historical_data_enabled") is not False:
        raise ValueError("Refusing import: manifest does not explicitly disable historical data.")
    if manifest.get("database_imported") is not False:
        raise ValueError("Refusing import: manifest must explicitly state database_imported=false.")
    reports = {
        item.get("dataset"): item
        for item in manifest.get("datasets", [])
        if isinstance(item, dict)
    }
    if not reports:
        raise ValueError("Manifest contains no dataset validation reports.")
    for dataset, report in reports.items():
        if report.get("season_validation") != "validated":
            raise ValueError(f"{dataset}: season column was not fully validated.")
        if report.get("season_null_rows") != 0:
            raise ValueError(f"{dataset}: null season rows are not allowed.")
        if report.get("distinct_season_values") != [CURRENT_SEASON]:
            raise ValueError(f"{dataset}: manifest does not prove an exclusive 2027 partition.")

    audit_path = folder / "quality-audit.json"
    if not audit_path.is_file():
        raise FileNotFoundError(f"Required quality audit not found: {audit_path}")
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    if audit.get("season") != CURRENT_SEASON or audit.get("database_imported") is not False:
        raise ValueError("Quality audit does not match the expected pre-import 2026-27 state.")
    audited = audit.get("datasets", {})
    for dataset, report in reports.items():
        audit_report = audited.get(dataset)
        if not audit_report or audit_report.get("rows") != report.get("rows"):
            raise ValueError(f"{dataset}: quality audit is missing or row count does not match.")
    return manifest


def _iter_records(path: Path, dataset: str) -> Iterable[tuple[int, dict[str, Any]]]:
    parquet = pq.ParquetFile(path)
    columns = parquet.schema_arrow.names
    if "season" not in columns:
        raise ValueError(f"{dataset}: no season column; refusing unverified season import.")
    row_number = 0
    for batch in parquet.iter_batches(batch_size=2_000):
        for record in batch.to_pylist():
            row_number += 1
            require_current_season(record.get("season"))
            yield row_number, _json_value(record)


def import_staged_raw(
    input_dir: str | Path,
    database_url: str,
    *,
    batch_size: int = 500,
) -> dict[str, Any]:
    """Import validated 2026-27 provider rows to PostgreSQL JSONB, idempotently."""
    database_url = _normalize_database_url(database_url)
    if batch_size < 1 or batch_size > 5_000:
        raise ValueError("batch_size must be between 1 and 5000.")

    folder = Path(input_dir)
    manifest = _validate_manifest(folder)
    listed = {
        item.get("dataset")
        for item in manifest.get("datasets", [])
        if isinstance(item, dict)
    }
    selected = sorted(name for name in DATASETS if name in listed)
    if not selected:
        raise ValueError("Manifest contains no supported NCAA MBB datasets.")

    # Complete all file, row-count and season checks before the first database write.
    preflight = {
        dataset: _preflight_dataset(
            folder,
            dataset,
            next(item for item in manifest["datasets"] if item.get("dataset") == dataset),
        )
        for dataset in selected
    }

    engine = create_engine(database_url, pool_pre_ping=True)
    totals: dict[str, dict[str, int]] = {}
    try:
        with engine.begin() as connection:
            connection.execute(text(TABLE_DDL))
        for dataset in selected:
            path = preflight[dataset]["path"]
            artifact_hash = preflight[dataset]["artifact_sha256"]
            pending: list[dict[str, Any]] = []
            seen = inserted = 0

            def flush(connection) -> None:
                nonlocal inserted
                if not pending:
                    return
                result = connection.execute(INSERT_SQL, pending)
                inserted += max(result.rowcount, 0)
                pending.clear()

            with engine.begin() as connection:
                for row_number, record in _iter_records(path, dataset):
                    seen += 1
                    pending.append({
                        "season": CURRENT_SEASON,
                        "dataset": dataset,
                        "source_file": path.name,
                        "artifact_sha256": artifact_hash,
                        "source_row_number": row_number,
                        "payload": json.dumps(record, ensure_ascii=False, separators=(",", ":")),
                    })
                    if len(pending) >= batch_size:
                        flush(connection)
                flush(connection)
            totals[dataset] = {
                "source_rows": seen,
                "inserted_rows": inserted,
                "already_present_rows": seen - inserted,
                "artifact_sha256": artifact_hash,
            }
    finally:
        engine.dispose()

    return {
        "season": CURRENT_SEASON,
        "season_label": CURRENT_SEASON_LABEL,
        "status": "completed",
        "storage": "postgresql_jsonb_raw_rows",
        "normalized_tables_created": False,
        "datasets": totals,
        "source_rows_total": sum(item["source_rows"] for item in totals.values()),
        "inserted_rows_total": sum(item["inserted_rows"] for item in totals.values()),
        "already_present_rows_total": sum(item["already_present_rows"] for item in totals.values()),
        "note": (
            "Raw source rows are preserved with artifact hashes and source row numbers. "
            "No inferred nationality, relational foreign keys, or normalized analytics "
            "were created by this import."
        ),
    }
