import pandas as pd
import pytest

from analytics import player_season_stats, team_season_stats


def test_player_stats_use_season_totals_for_shooting_rates():
    source = pd.DataFrame([
        {"season": 2027, "contest_id": "g1", "player_id": 10, "clean_name": "A Player",
         "team_ncaa_team_id": 1, "minutes": 30, "pts": 20, "fgm": 6, "fga": 10,
         "tpm": 2, "tpa": 4, "ftm": 6, "fta": 7, "ast": 4, "orb": 1, "drb": 3},
        {"season": 2027, "contest_id": "g2", "player_id": 10, "clean_name": "A Player",
         "team_ncaa_team_id": 1, "minutes": 32, "pts": 20, "fgm": 6, "fga": 10,
         "tpm": 2, "tpa": 4, "ftm": 2, "fta": 3, "ast": 2, "orb": 2, "drb": 5},
        {"season": 2027, "contest_id": "g1", "player_id": 20, "clean_name": "B Player",
         "team_ncaa_team_id": 2, "minutes": 15, "pts": 5, "fgm": 2, "fga": 5,
         "tpm": 1, "tpa": 2, "ftm": 0, "fta": 0, "ast": 1, "orb": 0, "drb": 1},
    ])
    result, meta = player_season_stats(source, min_games=1)
    a = result[result["Giocatore"] == "A Player"].iloc[0]
    assert a["Partite"] == 2
    assert a["Punti totali"] == 40
    assert a["Punti per partita"] == 20
    assert a["FG%"] == pytest.approx(0.6)
    assert a["eFG%"] == pytest.approx(0.7)
    assert a["TS%"] == pytest.approx(40 / (2 * (20 + 0.44 * 10)))
    assert meta["qualified_players"] == 2


def test_player_stats_keep_unresolved_ids_separate_and_flag_them():
    source = pd.DataFrame([
        {"season": 2027, "contest_id": "g1", "player_id": None, "clean_name": "Unknown",
         "team_ncaa_team_id": 11, "minutes": 10, "pts": 3},
        {"season": 2027, "contest_id": "g2", "player_id": None, "clean_name": "Unknown",
         "team_ncaa_team_id": 11, "minutes": 12, "pts": 5},
    ])
    result, meta = player_season_stats(source, min_games=1)
    assert len(result) == 1
    assert not bool(result.iloc[0]["Identità verificata"])
    assert meta["identity_unresolved"] == 1


def test_player_stats_reject_historical_season_rows():
    source = pd.DataFrame([
        {"season": 2026, "contest_id": "old", "player_id": 1, "clean_name": "Player",
         "minutes": 10, "pts": 4}
    ])
    with pytest.raises(ValueError, match="fuori dalla stagione"):
        player_season_stats(source)


def test_missing_values_are_not_converted_to_zero():
    source = pd.DataFrame([
        {"season": 2027, "contest_id": "g1", "player_id": 10, "clean_name": "A Player",
         "team_ncaa_team_id": 1, "minutes": 20, "pts": 10},
        {"season": 2027, "contest_id": "g2", "player_id": 10, "clean_name": "A Player",
         "team_ncaa_team_id": 1, "minutes": 20, "pts": None},
    ])
    result, _ = player_season_stats(source, min_games=1)
    row = result.iloc[0]
    assert row["Partite"] == 2
    assert row["Punti totali"] == 10
    assert row["Punti per partita"] == 10
    assert row["Punti gare con dato"] == 1


def test_team_stats_average_only_present_metrics():
    source = pd.DataFrame([
        {"season": 2027, "contest_id": "g1", "team_ncaa_team_id": 5,
         "offensive_rating": 110.0, "defensive_rating": 98.0, "possessions": 70},
        {"season": 2027, "contest_id": "g2", "team_ncaa_team_id": 5,
         "offensive_rating": 120.0, "defensive_rating": 102.0, "possessions": 75},
    ])
    result, meta = team_season_stats(source)
    row = result.iloc[0]
    assert row["Partite"] == 2
    assert row["ORtg"] == 115
    assert row["DRtg"] == 100
    assert row["Possessi"] == 72.5
    assert meta["teams"] == 1


def test_empty_inputs_are_reported_without_fake_rows():
    players, player_meta = player_season_stats(pd.DataFrame())
    teams, team_meta = team_season_stats(pd.DataFrame())
    assert players.empty and teams.empty
    assert player_meta["status"] == "empty"
    assert team_meta["status"] == "empty"
