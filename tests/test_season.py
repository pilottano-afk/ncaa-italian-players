import pytest

from ncaa_api.season import (
    CURRENT_SEASON,
    SeasonBoundaryError,
    filter_current_season,
    require_current_season,
)


def test_current_season_is_2027() -> None:
    assert CURRENT_SEASON == 2027
    assert require_current_season("2027") == 2027


@pytest.mark.parametrize("value", [2026, 2025, "2024", None, "unknown"])
def test_rejects_historical_or_invalid_seasons(value: object) -> None:
    with pytest.raises(SeasonBoundaryError):
        require_current_season(value)


def test_filter_accepts_only_current_season_records() -> None:
    rows = [{"season": 2027, "id": "g1"}, {"season": "2027", "id": "g2"}]
    assert [row["id"] for row in filter_current_season(rows)] == ["g1", "g2"]


def test_filter_rejects_mixed_historical_records() -> None:
    with pytest.raises(SeasonBoundaryError):
        filter_current_season([{"season": 2027}, {"season": 2026}])
