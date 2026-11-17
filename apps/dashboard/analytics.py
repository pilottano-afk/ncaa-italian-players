"""Season-level analytics derived only from imported NCAA 2026-27 box scores.

No historical seasons, inferred identities, or synthetic values are introduced.
"""
from __future__ import annotations

import re
import pandas as pd

SEASON = 2027
PLAYER_ALIASES = {
    "Minuti": ("minutes", "mins"),
    "Punti": ("pts", "points"),
    "Rimbalzi offensivi": ("orb", "oreb"),
    "Rimbalzi difensivi": ("drb", "dreb"),
    "Assist": ("ast", "assists"),
    "Palle rubate": ("stl", "steals"),
    "Stoppate": ("blk", "blocks"),
    "Palle perse": ("tov", "turnovers"),
    "Falli": ("pf", "personal_fouls"),
    "Tiri realizzati": ("fgm",),
    "Tiri tentati": ("fga",),
    "Triple realizzate": ("tpm", "fg3m"),
    "Triple tentate": ("tpa", "fg3a"),
    "Liberi realizzati": ("ftm",),
    "Liberi tentati": ("fta",),
    "Possessi offensivi": ("o_poss",),
}
NAME_FIELDS = ("clean_name", "player", "name", "athlete_display_name")
ID_FIELDS = ("player_id", "ncaa_player_id")
TEAM_FIELDS = ("team_ncaa_team_id", "team_id", "team", "team_name")
GAME_FIELDS = ("contest_id", "game_id")


def _column(frame: pd.DataFrame, aliases: tuple[str, ...]) -> str | None:
    return next((name for name in aliases if name in frame.columns), None)


def _numbers(frame: pd.DataFrame, aliases: tuple[str, ...]) -> pd.Series | None:
    col = _column(frame, aliases)
    return pd.to_numeric(frame[col], errors="coerce") if col else None


def _safe_name(value: object) -> str:
    if pd.isna(value):
        return "Giocatore non identificato"
    return re.sub(r"\s+", " ", str(value)).strip() or "Giocatore non identificato"


def player_season_stats(
    source: pd.DataFrame, *, min_games: int = 5
) -> tuple[pd.DataFrame, dict[str, object]]:
    """Aggregate player-game rows to season totals, per-game rates and valid percentiles."""
    if source.empty:
        return pd.DataFrame(), {"status": "empty", "season": SEASON}
    season_col = _column(source, ("season",))
    if season_col:
        seasons = set(pd.to_numeric(source[season_col], errors="coerce").dropna().astype(int))
        if seasons - {SEASON}:
            raise ValueError("Sono presenti record fuori dalla stagione 2026-27.")
    name_col = _column(source, NAME_FIELDS)
    if not name_col:
        return pd.DataFrame(), {"status": "missing_player_name", "season": SEASON}
    id_col = _column(source, ID_FIELDS)
    team_col = _column(source, TEAM_FIELDS)
    game_col = _column(source, GAME_FIELDS)
    work = source.copy()
    work["_name"] = work[name_col].map(_safe_name)
    work["_team"] = work[team_col].astype("string").fillna("team-unknown") if team_col else "team-unknown"
    if id_col:
        ids = work[id_col].astype("string")
        work["_identity"] = ids.where(ids.notna() & ids.ne(""), "unresolved:" + work["_team"].astype(str) + ":" + work["_name"])
    else:
        work["_identity"] = "unresolved:" + work["_team"].astype(str) + ":" + work["_name"]
    work["_game"] = work[game_col].astype("string") if game_col else work.index.astype(str)
    available = {}
    for label, aliases in PLAYER_ALIASES.items():
        values = _numbers(work, aliases)
        if values is not None:
            work["_m_" + label] = values
            available[label] = "_m_" + label
    if not available:
        return pd.DataFrame(), {"status": "no_recognized_box_score_metrics", "season": SEASON}
    grouped = work.groupby("_identity", dropna=False, sort=False)
    rows = []
    for identity, group in grouped:
        row: dict[str, object] = {
            "ID NCAA": identity if not str(identity).startswith("unresolved:") else None,
            "Giocatore": group["_name"].iloc[0],
            "Squadra ID": group["_team"].iloc[0],
            "Partite": int(group["_game"].nunique()),
            "Identità verificata": not str(identity).startswith("unresolved:"),
        }
        for label, col in available.items():
            row[label + " totali"] = group[col].sum(min_count=1)
            row[label] = group[col].mean()
        rows.append(row)
    result = pd.DataFrame(rows)
    games = result["Partite"].clip(lower=1)
    for label in available:
        result[label + " per partita"] = result[label + " totali"] / games
    # Recalculate shooting percentages from season totals; never average game percentages.
    def total(label: str) -> pd.Series | None:
        key = label + " totali"
        return pd.to_numeric(result[key], errors="coerce") if key in result else None
    fgm, fga = total("Tiri realizzati"), total("Tiri tentati")
    tpm, tpa = total("Triple realizzate"), total("Triple tentate")
    ftm, fta = total("Liberi realizzati"), total("Liberi tentati")
    pts = total("Punti")
    if fgm is not None and fga is not None:
        result["FG%"] = (fgm / fga.where(fga > 0)).where(fga > 0)
        if tpm is not None:
            result["eFG%"] = ((fgm + 0.5 * tpm) / fga.where(fga > 0)).where(fga > 0)
    if tpm is not None and tpa is not None:
        result["3P%"] = (tpm / tpa.where(tpa > 0)).where(tpa > 0)
    if ftm is not None and fta is not None:
        result["FT%"] = (ftm / fta.where(fta > 0)).where(fta > 0)
    if pts is not None and fga is not None and fta is not None:
        denominator = 2 * (fga + 0.44 * fta)
        result["TS%"] = (pts / denominator.where(denominator > 0)).where(denominator > 0)
    qualified = result["Partite"] >= min_games
    if "Minuti totali" in result:
        qualified &= result["Minuti totali"].fillna(0) > 0
    result["Campione percentile valido"] = qualified
    percentile_metrics = ["Punti per partita", "Assist per partita", "Rimbalzi offensivi per partita",
                          "Rimbalzi difensivi per partita", "TS%", "eFG%", "3P%", "FT%"]
    percentile_count = int(qualified.sum())
    for metric in percentile_metrics:
        if metric in result and percentile_count >= 2:
            values = pd.to_numeric(result.loc[qualified, metric], errors="coerce")
            valid = values.notna()
            pct = values[valid].rank(method="average", pct=True) * 100
            result["Percentile " + metric] = pd.NA
            result.loc[pct.index, "Percentile " + metric] = pct.round(1)
    return result.sort_values("Punti per partita", ascending=False, na_position="last") if "Punti per partita" in result else result, {
        "status": "ok",
        "season": SEASON,
        "source_rows": len(source),
        "players": len(result),
        "qualified_players": percentile_count,
        "min_games_for_percentile": min_games,
        "identity_unresolved": int((~result["Identità verificata"]).sum()),
        "percentile_population": "Giocatori con almeno min_games partite e minuti totali positivi; solo stagione 2026-27.",
        "shooting_formula": "TS%=PTS/[2*(FGA+0.44*FTA)]; eFG%=(FGM+0.5*3PM)/FGA.",
    }


def team_season_stats(source: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, object]]:
    """Aggregate team-game records without fabricating unavailable possessions or ratings."""
    if source.empty:
        return pd.DataFrame(), {"status": "empty", "season": SEASON}
    season_col = _column(source, ("season",))
    if season_col:
        seasons = set(pd.to_numeric(source[season_col], errors="coerce").dropna().astype(int))
        if seasons - {SEASON}:
            raise ValueError("Sono presenti record fuori dalla stagione 2026-27.")
    team_col = _column(source, ("team_ncaa_team_id", "team_id", "team", "team_name"))
    if not team_col:
        return pd.DataFrame(), {"status": "missing_team_id", "season": SEASON}
    metrics = {
        "Possessi": ("possessions",), "ORtg": ("offensive_rating", "ORtg", "ortg"),
        "DRtg": ("defensive_rating", "DRtg", "drtg"), "NetRtg": ("net_rating", "NetRtg", "netrtg"),
        "Punti": ("pts", "points"), "TS%": ("ts_pct",), "eFG%": ("efg_pct",),
        "TOV%": ("tov_pct",), "ORB%": ("orb_pct",), "DRB%": ("drb_pct",),
    }
    work = source.copy()
    work["_team"] = work[team_col].astype("string").fillna("Squadra non identificata")
    rows = []
    for team, group in work.groupby("_team", dropna=False):
        row = {"Squadra ID": str(team), "Partite": group[_column(group, GAME_FIELDS)].nunique()
               if _column(group, GAME_FIELDS) else len(group)}
        for label, aliases in metrics.items():
            values = _numbers(group, aliases)
            if values is not None:
                row[label] = values.mean()
        rows.append(row)
    result = pd.DataFrame(rows)
    for col in result.select_dtypes(include="number").columns:
        result[col] = result[col].round(2)
    return result, {"status": "ok", "season": SEASON, "teams": len(result),
                    "source_rows": len(source)}
