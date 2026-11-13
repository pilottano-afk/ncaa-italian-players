from pathlib import Path

import pytest

from ncaa_api.providers.sportsdataverse import SportsDataverseClient


def test_builds_release_url_for_2026_27_player_box() -> None:
    assert SportsDataverseClient.dataset_url("player_box") == (
        "https://github.com/sportsdataverse/sportsdataverse-data/releases/download/"
        "ncaa_mbb_player_box/ncaa_mbb_player_box_2027.parquet"
    )


@pytest.mark.parametrize("season", [2026, 2025, 2024])
def test_never_builds_historical_release_url(season: int) -> None:
    with pytest.raises(ValueError, match="only stores 2026-27"):
        SportsDataverseClient.dataset_url("player_box", season)


def test_rejects_unknown_dataset() -> None:
    with pytest.raises(ValueError, match="Unsupported NCAA MBB dataset"):
        SportsDataverseClient.dataset_url("invented_dataset")


def test_validates_parquet_magic_bytes(tmp_path: Path) -> None:
    good = tmp_path / "good.parquet"
    good.write_bytes(b"PAR1some parquet bytesPAR1")
    SportsDataverseClient.validate_parquet(good)

    bad = tmp_path / "bad.parquet"
    bad.write_bytes(b"not parquet")
    with pytest.raises(ValueError, match="not a valid Parquet"):
        SportsDataverseClient.validate_parquet(bad)
