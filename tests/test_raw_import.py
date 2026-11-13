from datetime import date, datetime, timezone
from decimal import Decimal
import json
import math
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from ncaa_api.raw_import import _iter_records, _json_value, _normalize_database_url, _validate_manifest


def test_json_value_preserves_common_arrow_python_types() -> None:
    value = {
        "day": date(2026, 11, 13),
        "timestamp": datetime(2026, 11, 13, tzinfo=timezone.utc),
        "decimal": Decimal("12.340"),
        "binary": b"abc",
        "nested": [1, None],
        "nan": float("nan"),
        "infinity": float("inf"),
    }
    normalized = _json_value(value)
    assert normalized["day"] == "2026-11-13"
    assert normalized["timestamp"].startswith("2026-11-13T")
    assert normalized["decimal"] == "12.340"
    assert normalized["binary"]["value"] == "YWJj"
    assert normalized["nested"] == [1, None]
    assert normalized["nan"]["value"] == "NaN"
    assert normalized["infinity"]["value"] == "Infinity"


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


def write_valid_import_metadata(folder: Path) -> None:
    report = {
        "dataset": "schedule",
        "rows": 1,
        "season_validation": "validated",
        "season_null_rows": 0,
        "distinct_season_values": [2027],
    }
    manifest = {
        "season": 2027,
        "historical_data_enabled": False,
        "database_imported": False,
        "datasets": [report],
    }
    audit = {
        "season": 2027,
        "database_imported": False,
        "datasets": {"schedule": {"rows": 1}},
    }
    (folder / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    (folder / "quality-audit.json").write_text(json.dumps(audit), encoding="utf-8")


def test_validate_manifest_requires_matching_audit(tmp_path: Path) -> None:
    write_valid_import_metadata(tmp_path)
    assert _validate_manifest(tmp_path)["season"] == 2027

    audit = json.loads((tmp_path / "quality-audit.json").read_text(encoding="utf-8"))
    audit["datasets"]["schedule"]["rows"] = 2
    (tmp_path / "quality-audit.json").write_text(json.dumps(audit), encoding="utf-8")
    with pytest.raises(ValueError, match="row count does not match"):
        _validate_manifest(tmp_path)


def test_validate_manifest_rejects_unvalidated_season(tmp_path: Path) -> None:
    write_valid_import_metadata(tmp_path)
    manifest = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    manifest["datasets"][0]["season_validation"] = "partition_tag_only"
    (tmp_path / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="not fully validated"):
        _validate_manifest(tmp_path)


def test_validate_manifest_requires_history_disabled(tmp_path: Path) -> None:
    write_valid_import_metadata(tmp_path)
    manifest = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    manifest["historical_data_enabled"] = True
    (tmp_path / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="historical data"):
        _validate_manifest(tmp_path)


def test_database_url_uses_psycopg3_driver() -> None:
    assert _normalize_database_url("postgresql://user:pass@localhost/db") == (
        "postgresql+psycopg://user:pass@localhost/db"
    )
    assert _normalize_database_url("postgresql+psycopg://user:pass@localhost/db") == (
        "postgresql+psycopg://user:pass@localhost/db"
    )
    with pytest.raises(ValueError, match="PostgreSQL"):
        _normalize_database_url("sqlite:///not-supported.db")
