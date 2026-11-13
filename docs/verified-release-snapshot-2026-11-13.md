# Verified SportsDataverse release snapshot — 2026-11-13

Checked against the GitHub Releases API on 2026-11-13. All eleven listed release tags contained a Parquet asset whose filename ends in `_2027.parquet`. These are existence checks only: they do not prove that every NCAA game/team/player is represented, nor that every field is populated.

| Dataset | Asset | Size (bytes) | Asset updated (UTC) |
|---|---|---:|---|
| schedule | `ncaa_mbb_schedule_2027.parquet` | 11,141 | 2026-11-12 12:30:40 |
| team_rosters | `ncaa_mbb_team_rosters_2027.parquet` | 241,816 | 2026-11-04 02:46:58 |
| rosters | `ncaa_mbb_rosters_2027.parquet` | 53,841 | 2026-11-12 12:31:10 |
| pbp | `ncaa_mbb_pbp_2027.parquet` | 5,870,944 | 2026-11-12 12:31:57 |
| player_box | `ncaa_mbb_player_box_2027.parquet` | 1,118,026 | 2026-11-12 12:32:25 |
| team_box | `ncaa_mbb_team_box_2027.parquet` | 181,372 | 2026-11-12 12:32:52 |
| lineups | `ncaa_mbb_lineups_2027.parquet` | 1,706,100 | 2026-11-12 12:33:24 |
| matchup_stints | `ncaa_mbb_matchup_stints_2027.parquet` | 1,181,353 | 2026-11-12 12:34:03 |
| possessions | `ncaa_mbb_possessions_2027.parquet` | 1,380,919 | 2026-11-12 12:34:34 |
| shots | `ncaa_mbb_shots_2027.parquet` | 908,795 | 2026-11-12 12:35:02 |
| team_ids | `ncaa_mbb_team_ids_2027.parquet` | 5,125 | 2026-11-01 12:46:28 |

## Interpretation

- The 2026-27 partition is published for all eleven dataset families.
- The team roster asset is older than the game-level assets; roster freshness must be monitored separately.
- Team IDs are the oldest asset in this snapshot and should be refreshed/compared before relying on them as a complete crosswalk.
- File existence and timestamp are not coverage metrics. The ingestion pipeline must inspect schemas, row counts, duplicate keys, game coverage, and null rates before data is exposed in the app.
- No historical partition is to be downloaded by this project.

## References

- Producer and dataset definitions: https://github.com/sportsdataverse/ncaa-mbb-hoops-data
- Release assets: https://github.com/sportsdataverse/sportsdataverse-data/releases
- Loader asset URL and field documentation: https://py.sportsdataverse.org/docs/mbb/reference/loaders/ncaa
