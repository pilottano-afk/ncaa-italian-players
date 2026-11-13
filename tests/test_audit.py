from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from ncaa_api.audit import audit_staged_data


def write_dataset(folder: Path, name: str, data: dict) -> None:
    table = pa.table(data)
    pq.write_table(table, folder / f"ncaa_mbb_{name}_2027.parquet")


def test_audit_measures_candidate_keys_and_join_coverage(tmp_path: Path) -> None:
    write_dataset(
        tmp_path, "schedule",
        {"contest_id": ["g1", "g2"], "season": [2027, 2027]},
    )
    write_dataset(
        tmp_path, "player_box",
        {
            "contest_id": ["g1", "g1", "g2"],
            "player_id": ["p1", "p2", "p1"],
            "team_ncaa_team_id": ["t1", "t1", "t1"],
            "season": [2027, 2027, 2027],
        },
    )
    write_dataset(
        tmp_path, "team_rosters",
        {"player_id": ["p1", "p2"], "team_id": ["t1", "t1"], "season": [2027, 2027]},
    )
    write_dataset(tmp_path, "team_ids", {"id": ["t1"], "season": [2027]})

    report = audit_staged_data(tmp_path)
    player_key = report["datasets"]["player_box"]["candidate_keys"][0]
    assert player_key["duplicate_key_groups"] == 0
    joins = {
        (item["from"], item["to"]): item
        for item in report["candidate_joins"]
    }
    assert joins[("player_box.contest_id", "schedule.contest_id")]["coverage_pct"] == 100.0
    assert joins[("player_box.player_id", "team_rosters.player_id")]["coverage_pct"] == 100.0
    assert joins[("team_rosters.team_id", "team_ids.id")]["coverage_pct"] == 100.0
    assert report["database_imported"] is False


def test_audit_reports_duplicate_candidate_keys(tmp_path: Path) -> None:
    write_dataset(
        tmp_path, "schedule",
        {"contest_id": ["g1", "g1"], "season": [2027, 2027]},
    )
    report = audit_staged_data(tmp_path)
    key = report["datasets"]["schedule"]["candidate_keys"][0]
    assert key["duplicate_key_groups"] == 1
    assert key["duplicate_rows_beyond_first"] == 1


def test_audit_rejects_historical_season(tmp_path: Path) -> None:
    write_dataset(tmp_path, "schedule", {"contest_id": ["g1"], "season": [2026]})
    with pytest.raises(ValueError, match="only stores 2026-27"):
        audit_staged_data(tmp_path)
