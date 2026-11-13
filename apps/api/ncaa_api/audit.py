"""Quality audit for staged NCAA Parquet datasets (no database writes)."""
from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pyarrow.parquet as pq

from ncaa_api.season import CURRENT_SEASON, CURRENT_SEASON_LABEL, require_current_season
from ncaa_api.providers.sportsdataverse import DATASETS, SportsDataverseClient


CANDIDATE_KEYS = {
    "schedule": [("contest_id",)],
    "team_rosters": [("season", "team_id", "player_id")],
    "player_box": [("contest_id", "player_id")],
    "team_box": [("contest_id", "team_ncaa_team_id")],
    "possessions": [("contest_id", "poss_num")],
    "matchup_stints": [("contest_id", "game_stint_num")],
    "team_ids": [("season", "id")],
}
JOIN_CANDIDATES = (
    ("player_box", "contest_id", "schedule", "contest_id"),
    ("team_box", "contest_id", "schedule", "contest_id"),
    ("pbp", "contest_id", "schedule", "contest_id"),
    ("possessions", "contest_id", "schedule", "contest_id"),
    ("shots", "contest_id", "schedule", "contest_id"),
    ("lineups", "contest_id", "schedule", "contest_id"),
    ("matchup_stints", "contest_id", "schedule", "contest_id"),
    ("player_box", "player_id", "team_rosters", "player_id"),
    ("team_rosters", "team_id", "team_ids", "id"),
    ("player_box", "team_ncaa_team_id", "team_ids", "id"),
)


def _read_dataset(folder: Path, name: str):
    path = folder / f"ncaa_mbb_{name}_{CURRENT_SEASON}.parquet"
    if not path.exists():
        raise FileNotFoundError(f"Missing staged dataset: {path}")
    SportsDataverseClient.validate_parquet(path)
    return pq.read_table(path)


def _key_report(table, keys: tuple[str, ...]) -> dict[str, Any]:
    missing_columns = [key for key in keys if key not in table.column_names]
    if missing_columns:
        return {"columns": list(keys), "status": "missing_columns", "missing": missing_columns}
    tuples = zip(*(table.column(key).to_pylist() for key in keys))
    counts = Counter(tuple(values) for values in tuples if all(v is not None for v in values))
    duplicates = [(key, count) for key, count in counts.items() if count > 1]
    return {
        "columns": list(keys),
        "status": "measured",
        "complete_key_rows": sum(counts.values()),
        "distinct_keys": len(counts),
        "duplicate_key_groups": len(duplicates),
        "duplicate_rows_beyond_first": sum(count - 1 for _, count in duplicates),
        "duplicate_samples": [
            {"key": list(key), "count": count} for key, count in duplicates[:5]
        ],
    }


def audit_staged_data(input_dir: str | Path, output_path: str | Path | None = None) -> dict[str, Any]:
    """Measure nulls, candidate duplicate keys, and cross-dataset join coverage."""
    folder = Path(input_dir)
    tables = {name: _read_dataset(folder, name) for name in sorted(DATASETS)
              if (folder / f"ncaa_mbb_{name}_{CURRENT_SEASON}.parquet").exists()}
    if not tables:
        raise FileNotFoundError(f"No NCAA {CURRENT_SEASON} Parquet datasets found in {folder}")

    datasets: dict[str, Any] = {}
    value_sets: dict[tuple[str, str], set[Any]] = {}
    for name, table in tables.items():
        if "season" in table.column_names:
            seasons = set(table.column("season").drop_null().to_pylist())
            for season in seasons:
                require_current_season(season)
        nulls = {
            field: table.column(field).null_count
            for field in table.column_names
            if table.column(field).null_count
        }
        key_reports = [
            _key_report(table, key) for key in CANDIDATE_KEYS.get(name, ())
        ]
        datasets[name] = {
            "rows": table.num_rows,
            "columns": len(table.column_names),
            "nonzero_null_counts": nulls,
            "candidate_keys": key_reports,
        }
        for field in table.column_names:
            if (name, field) in {
                ("schedule", "contest_id"),
                ("player_box", "contest_id"), ("team_box", "contest_id"),
                ("pbp", "contest_id"), ("possessions", "contest_id"),
                ("shots", "contest_id"), ("lineups", "contest_id"),
                ("matchup_stints", "contest_id"), ("player_box", "player_id"),
                ("team_rosters", "player_id"), ("team_rosters", "team_id"),
                ("player_box", "team_ncaa_team_id"), ("team_ids", "id"),
            }:
                value_sets[(name, field)] = {
                    value for value in table.column(field).to_pylist() if value is not None
                }

    joins = []
    for left_table, left_col, right_table, right_col in JOIN_CANDIDATES:
        left_key, right_key = (left_table, left_col), (right_table, right_col)
        if left_key not in value_sets or right_key not in value_sets:
            joins.append({
                "from": f"{left_table}.{left_col}",
                "to": f"{right_table}.{right_col}",
                "status": "dataset_or_column_missing",
            })
            continue
        left_values, right_values = value_sets[left_key], value_sets[right_key]
        matched = left_values & right_values
        joins.append({
            "from": f"{left_table}.{left_col}",
            "to": f"{right_table}.{right_col}",
            "status": "measured",
            "distinct_source_values": len(left_values),
            "matched_distinct_values": len(matched),
            "unmatched_distinct_values": len(left_values - right_values),
            "coverage_pct": round(100 * len(matched) / len(left_values), 2) if left_values else None,
            "unmatched_samples": sorted(left_values - right_values, key=str)[:5],
        })

    report = {
        "season": CURRENT_SEASON,
        "season_label": CURRENT_SEASON_LABEL,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "database_imported": False,
        "datasets": datasets,
        "candidate_joins": joins,
        "limitations": [
            "Candidate keys and joins are diagnostics, not enforced constraints.",
            "Join coverage is based on distinct non-null values, not row-level foreign-key coverage.",
            "No player nationality is inferred from these files.",
            "No claim of complete season coverage is made.",
        ],
    }
    if output_path:
        destination = Path(output_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report
