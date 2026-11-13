from datetime import date, datetime, timezone
from decimal import Decimal
import json
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from ncaa_api.raw_import import _iter_records, _json_value, _validate_manifest


def test_json_value_preserves_common_arrow_python_types() -> None:
    value = {
        "day": date(2026, 11, 13),
        "timestamp": datetime(2026, 11, 13, tzinfo=timezone.utc),
        "decimal": Decimal("12.340"),
        "binary": b"abc",
        "nested": [1, None],
    }
    normalized = _json_value(value)
    assert normalized["day"] == "2026-11-13"
    assert normalized["timestamp"].startswith("2026-11-13T")
    assert normalized["decimal"] == "12.340"
    assert normalized["binary"]["value"] == "YWJj"
    assert normalized["nested"] == [1, None]


def test_iter_records_requires_current_season(tmp_path: Path) -> None:
    path = tmp_path / "schedule.parquet"
    pq.write_table(pa.table({"contest_id": ["g1"], "season": [2027]}), path)
    rows = list(_iter_records(path, "schedule"))
    assert rows == [(1, {"contest_id": "g1", "season": 2027})]


def test_iter_records_rejects_historical_season(tmp_path: Path) -> None:
    path = tmp_path / "schedule.parquet"
    pq.write_table(pa.table({"contest_id": ["g1"], "season": [2026]}), path)
    with pytest.raises(ValueError, match="only stores 2026-27"):
        list(_iter_records(path, "schedule"))


def test_validate_manifest_requires_current_season_and_history_disabled(tmp_path: Path) -> None:
    manifest = {
        "season": 2027,
        "historical_data_enabled": False,
        "database_imported": False,
        "datasets": [{"dataset": "schedule"}],
    }
    (tmp_path / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    assert _validate_manifest(tmp_path)["season"] == 2027

    manifest["historical_data_enabled"] = True
    (tmp_path / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="historical data"):
        _validate_manifest(tmp_path)
