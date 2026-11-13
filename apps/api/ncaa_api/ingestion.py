"""Season-locked staging ingestion and schema/coverage inspection for NCAA Parquet."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pyarrow.parquet as pq

from ncaa_api.season import CURRENT_SEASON, CURRENT_SEASON_LABEL, require_current_season
from ncaa_api.providers.sportsdataverse import DATASETS, SportsDataverseClient


DEFAULT_BOOTSTRAP_DATASETS = ("schedule", "rosters", "player_box")


def inspect_parquet(path: str | Path, dataset: str) -> dict[str, Any]:
    """Inspect physical file metadata and schema without assuming provider columns."""
    if dataset not in DATASETS:
        raise ValueError(f"Unsupported NCAA MBB dataset: {dataset}")
    file_path = Path(path)
    SportsDataverseClient.validate_parquet(file_path)
    parquet = pq.ParquetFile(file_path)
    schema = parquet.schema_arrow
    names = schema.names
    row_count = parquet.metadata.num_rows
    season_status = "partition_tag_only"
    distinct_seasons: set[int] = set()
    season_null_rows = 0
    season_non_null_rows = 0

    if "season" in names:
        for batch in parquet.iter_batches(columns=["season"], batch_size=50_000):
            for value in batch.column(0).to_pylist():
                if value is None:
                    season_null_rows += 1
                    continue
                distinct_seasons.add(require_current_season(value))
                season_non_null_rows += 1
        if row_count and season_non_null_rows == 0:
            season_status = "season_column_all_null"
        elif season_null_rows:
            season_status = "season_column_contains_nulls"
        else:
            season_status = "validated"

    validation = (
        "passed"
        if season_status in {"validated", "partition_tag_only"}
        else "warning"
    )
    return {
        "dataset": dataset,
        "season": CURRENT_SEASON,
        "season_label": CURRENT_SEASON_LABEL,
        "file": file_path.name,
        "file_size_bytes": file_path.stat().st_size,
        "rows": row_count,
        "row_groups": parquet.metadata.num_row_groups,
        "columns": [
            {"name": field.name, "type": str(field.type), "nullable": field.nullable}
            for field in schema
        ],
        "season_validation": season_status,
        "season_non_null_rows": season_non_null_rows,
        "season_null_rows": season_null_rows,
        "distinct_season_values": sorted(distinct_seasons),
        "inspected_at": datetime.now(timezone.utc).isoformat(),
        "validation": validation,
    }


def stage_bootstrap_data(
    output_dir: str | Path = "data/staging/2027",
    datasets: tuple[str, ...] = DEFAULT_BOOTSTRAP_DATASETS,
    *,
    client: SportsDataverseClient | None = None,
) -> dict[str, Any]:
    """Download and inspect selected 2026-27 assets; write a machine-readable manifest."""
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    provider = client or SportsDataverseClient()
    reports: list[dict[str, Any]] = []

    for dataset in datasets:
        if dataset not in DATASETS:
            raise ValueError(f"Unsupported NCAA MBB dataset: {dataset}")
        destination = output / f"ncaa_mbb_{dataset}_{CURRENT_SEASON}.parquet"
        provider.download(dataset, destination, CURRENT_SEASON)
        reports.append(inspect_parquet(destination, dataset))

    has_warnings = any(report["validation"] != "passed" for report in reports)
    manifest = {
        "season": CURRENT_SEASON,
        "season_label": CURRENT_SEASON_LABEL,
        "historical_data_enabled": False,
        "source": "SportsDataverse NCAA MBB releases",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "datasets": reports,
        "status": "schema_review_required" if has_warnings else "staged_for_schema_review",
        "database_imported": False,
        "note": (
            "Files are staged locally. A partition filename is not proof that every "
            "record belongs to the season; null or missing season values require review. "
            "Review actual provider schemas and coverage before normalized database import."
        ),
    }
    manifest_path = output / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest
