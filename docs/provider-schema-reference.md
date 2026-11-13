# SportsDataverse NCAA MBB schema reference

Status: **documentation-derived reference, not a validation of the 2027 Parquet assets**.  
Season in scope: 2026-27 (season=2027).

The source loader documentation describes the following fields. The actual downloaded 2027 files must still be inspected by ncaa-stage before database mapping is finalized.

Source documentation: https://py.sportsdataverse.org/docs/mbb/reference/loaders/ncaa  
Dataset lineage: https://github.com/sportsdataverse/ncaa-mbb-hoops-data

## Dataset roles and candidate join keys

| Dataset | Purpose | Documented identifiers / fields |
|---|---|---|
| schedule | Game calendar and final scores | contest_id, game_date, home, away, scores, season |
| team_rosters | Detailed team-season roster | team_id, player_id, player, clean_name, name, jersey, class, position, height, hometown, high_school, season |
| rosters | Players with game participation | team, player, games, season; no player ID documented here |
| player_box | Player-game box score and advanced splits | contest_id, player_id, clean_name, team_ncaa_team_id, team_espn_team_id, season, minutes, possessions and shooting/box metrics |
| team_box | Team-game ratings and four factors | contest_id, team_ncaa_team_id, team_espn_team_id, season, possessions, ORtg, DRtg, NetRtg and shooting/rebounding/turnover rates |
| pbp | Event-level play-by-play | game_date, period, clock, event_type, player_1, player_2, possession fields, season |
| possessions | Possession-level records and on-court players | poss_num, player IDs / clean names in lineup slots, game identifiers, season |
| lineups | Five-player lineup stints | lineup_key, lineup_id, contest_id, team, stint timing, possessions, points and opponent splits, season |
| shots | Shot-chart events | contest_id, shooter_player_id, shooter_clean_name, shot_x, shot_y, dist_ft, shot_zone, made, point_value |

## Important player_box metrics documented by the provider

Basic box score: mins, pts, orb, drb, ast, stl, blk, tov, pf.

Efficiency and shooting: ts_pct, efg_pct, fgm, fga, fg_pct, tpm, tpa, tp_pct, ftm, fta, ft_pct.

Shot-location splits: rimm, rima, rim_pct, midm, mida, mid_pct, plus putback and assisted/unassisted splits.

Possession context: o_poss and half-court splits such as orb_half, drb_half, ast_half, stl_half, blk_half, tov_half, ts_pct_half.

## Modeling implications

1. Prefer player_id and contest_id over player names for joins when both are present.
2. Treat clean_name as a secondary reconciliation key, not a globally unique player ID.
3. Do not assume rosters alone contains full active rosters: its documented lineage is derived from player box-score participation. Use team_rosters for roster discovery and reconcile it with game participation.
4. The detailed team_rosters fields include hometown, not a guaranteed nationality field. Italian nationality must be verified from reliable independent evidence.
5. shots documentation currently describes some time/period fields as all-null. The app must show unavailable data rather than fabricate shot-clock or period values.
6. Possession and lineup datasets have separate grain. Do not join them to player-game rows without an explicit game/team/player or lineup key strategy.
7. Percentile calculations must use comparable Division I players and the same season; define minimum minutes/possessions before publishing leaderboards.

## Gate before normalized import

- Run staging against the actual season 2027 assets.
- Save the manifest and physical schema reports.
- Compare every actual column and type with this reference.
- Check null rates and duplicate candidate keys.
- Confirm actual season values and cross-dataset identifier coverage.
- Only then create migrations and normalized import mappings.
