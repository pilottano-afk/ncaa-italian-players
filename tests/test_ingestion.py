import json
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from ncaa_api.ingestion import inspect_parquet


def write_parquet(path: Path, table: pa.Table) -> None:
    pq.write_table(table, path)


def test_inspects_current_season_parquet(tmp_path: Path) -> None:
    path = tmp_path / "players.parquet"
    write_parquet(path, pa.table({"season": [2027, 2027], "athlete_id": [10, 11]}))
    report = inspect_parquet(path, "player_box")
    assert report["rows"] == 2
    assert report["season_validation"] == "validated"
    assert report["distinct_season_values"] == [2027]
    assert report["validation"] == "passed"


def test_rejects_historical_season_inside_parquet(tmp_path: Path) -> None:
    path = tmp_path / "mixed.parquet"
    write_parquet(path, pa.table({"season": [2027, 2026]}))
    with pytest.raises(ValueError, match="only stores 2026-27"):
        inspect_parquet(path, "rosters")


def test_marks_partition_only_when_no_season_column(tmp_path: Path) -> None:
    path = tmp_path / "schedule.parquet"
    write_parquet(path, pa.table({"game_id": ["g1"], "home_team": ["A"]}))
    report = inspect_parquet(path, "schedule")
    assert report["season_validation"] == "partition_tag_only"
    assert report["season"] == 2027


def test_manifest_policy_is_not_claimed_as_database_import(tmp_path: Path) -> None:
    # The CLI staging layer deliberately reports database_imported=False.
    path = tmp_path / "one.parquet"
    write_parquet(path, pa.table({"season": [2027]}))
    assert inspect_parquet(path, "player_box")["validation"] == "passed"
