# Verified NCAA 2026-27 staging audit

Audit source: uploaded GitHub Actions artifact `ncaa-2027-staging-43403681058.zip`.
Manifest generated: 2026-11-13 09:43:47 UTC.
Provider: SportsDataverse NCAA MBB releases.
Season partition: 2027 (2026-27). Historical data enabled: false.
Database imported: false.

## Verified inventory

All 11 files passed the season-column validation recorded by PyArrow: each has only season value 2027 and zero null season rows.

| Dataset | Rows | Columns |
|---|---:|---:|
| schedule | 482 | 7 |
| team_rosters | 5,587 | 16 |
| rosters | 6,321 | 4 |
| pbp | 253,740 | 87 |
| player_box | 11,392 | 125 |
| team_box | 964 | 81 |
| lineups | 23,505 | 77 |
| matchup_stints | 17,283 | 33 |
| possessions | 70,350 | 56 |
| shots | 58,313 | 19 |
| team_ids | 365 | 4 |

These are row counts, not unique games, players, completed games, or proof of complete coverage. Null rates outside the season field, duplicate keys, and join coverage have not yet been measured.

## Actual schema highlights

- schedule: contest_id, game_date, home, away, home_score, away_score, season.
- team_rosters: season, team_id, team, player_id, player, clean_name, name, jersey, class, position, height, ht_inches, hometown, high_school, gp, gs.
- rosters: season, team, player, games.
- player_box: contest_id, team_ncaa_team_id, team_espn_team_id, player_id, clean_name, espn_game_id, season, minutes, possessions, box-score, shooting and split metrics (125 columns total).
- team_box: contest_id, team_ncaa_team_id, team_espn_team_id, espn_game_id, season, offensive/defensive ratings, possessions, four factors and shooting splits (81 columns total).
- pbp: contest_id, event/game context, event_type/result, player IDs and clean names, possession fields, five-player home/away lineup slots, season (87 columns total).
- possessions: contest_id, poss_num, poss_team, player IDs and clean names for on-court lineup slots, scores and possession features (56 columns total).
- lineups: contest_id, lineup_key, lineup_id, team/opponent, five player slots, stint/possession and box-score totals (77 columns total).
- matchup_stints: contest_id, game_stint_num, home_lineup_key, away_lineup_key, home/away lineup player slots, duration and score changes (33 columns total).
- shots: contest_id, shooter_player_id, shooter_clean_name, team IDs, shot_x, shot_y, dist_ft, shot_zone, shot_type, made, point_value, period, sec_left, source (19 columns total).
- team_ids: team, conference, id, season.

## Proposed normalized model

1. teams and a separate source-ID crosswalk;
2. players and source-name aliases;
3. games keyed by contest_id;
4. player_game_stats from player_box;
5. team_game_stats from team_box;
6. roster_memberships primarily from team_rosters;
7. separate play_by_play, possessions, lineups, matchup_stints and shots fact tables.

Do not flatten event-, possession-, lineup- or shot-grain data into player-game rows.

## Candidate joins and keys to validate

- schedule.contest_id to the contest_id fields in player_box, team_box, pbp, possessions, shots, lineups and matchup_stints.
- player_box.player_id to team_rosters.player_id.
- team_rosters.team_id and player_box.team_ncaa_team_id to team_ids.id.
- Candidate uniqueness: schedule(contest_id), player_box(contest_id, player_id), team_box(contest_id, team_ncaa_team_id), possessions(contest_id, poss_num), matchup_stints(contest_id, game_stint_num).

These are hypotheses to test against actual values, null rates, duplicate counts and join coverage before enforcing constraints.

## Italian-player verification

team_rosters contains hometown and high-school fields, not an explicit nationality field. Italian nationality must be verified independently from official university biographies, national-team records or other reliable primary sources. Never infer nationality from a name or hometown. Store evidence URL, checked date and verification status.

## Next milestone

Implement a repeatable data-quality audit for null rates, candidate duplicate keys and cross-dataset join coverage. Review its report before adding PostgreSQL migrations and import mappings. The NBA Draft 2027 Top 30 remains a separate prospect dataset.
