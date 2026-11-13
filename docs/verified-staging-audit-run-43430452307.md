# Verified NCAA 2026-27 staging audit — run 43430452307

- Artifact: `ncaa-2027-staging-43430452307.zip`
- Generated: 2026-11-13 13:04 UTC
- Season: 2026-27 (`season=2027`)
- Manifest status: `staged_for_schema_review`
- Database imported: **no**
- Historical data enabled: **no**

## Season validation

All 11 datasets passed the manifest's season check. Each has zero null season values and only the value `2027`.

| Dataset | Rows |
|---|---:|
| schedule | 689 |
| team_rosters | 5,587 |
| rosters | 7,201 |
| player_box | 16,159 |
| team_box | 1,378 |
| pbp | 361,352 |
| lineups | 33,181 |
| matchup_stints | 24,549 |
| possessions | 100,798 |
| shots | 83,679 |
| team_ids | 365 |

These are provider rows, not counts of unique games, players, or teams.

## Candidate key checks

No duplicate groups were found among complete values for the configured candidate keys:

| Dataset | Candidate key | Complete rows | Duplicate groups |
|---|---|---:|---:|
| schedule | contest_id | 689 | 0 |
| team_rosters | season, team_id, player_id | 5,587 | 0 |
| player_box | contest_id, player_id | 13,474 | 0 |
| team_box | contest_id, team_ncaa_team_id | 1,181 | 0 |
| possessions | contest_id, poss_num | 100,798 | 0 |
| matchup_stints | contest_id, game_stint_num | 24,549 | 0 |
| team_ids | season, id | 365 | 0 |

Important: `player_box` has 2,685 rows without `player_id` (16.6%); `team_box` has 197 rows without `team_ncaa_team_id` (14.3%). The no-duplicate result applies only to rows with complete candidate-key values. Do not enforce these as unconditional database uniqueness constraints until null handling and provider semantics are resolved.

## Candidate join coverage

The audit found 100% distinct-value coverage for all configured joins:
- Each of player_box, team_box, pbp, possessions, lineups and matchup_stints contest IDs matched schedule contest IDs.
- 688 distinct shot contest IDs matched schedule (100% of shot contest IDs).
- All 4,839 distinct non-null player IDs in player_box matched team_rosters.
- All 365 team_rosters team IDs matched team_ids.
- All 365 distinct non-null player_box NCAA team IDs matched team_ids.

This is distinct-value coverage, not row-level foreign-key coverage. It does not establish that every record is complete or that the season is fully covered.

## Nulls and interpretation

Some nulls are expected for event-specific fields: for example, PBP player_2_id is null in 95.0% of rows, and shot/event result fields are naturally inapplicable to many event types. They must not be converted to zero or treated as universal data errors.

Fields needing explicit review:
- `player_box.player_id` and `clean_name`: 2,685 null rows each.
- `player_box.team_ncaa_team_id`: 2,629 null rows.
- `team_box.team_ncaa_team_id`: 197 null rows.
- `shots.shooter_player_id`: 12,065 null rows (14.4%).
- `pbp.player_1_id`: 61,511 null rows (17.0%); `player_2_id` is event-dependent.
- `lineups.player_count_error`: null in all 33,181 rows; treat as unavailable/not populated, not as a zero-valued metric.

## Decision

**The staging and audit workflow completed successfully and the data passes the season partition check. It is not yet ready for a blind import into production tables.**

Next engineering step: define the normalized schema and a conservative import that preserves source rows and nulls, stages unresolved player/team IDs, and reports row-level linkage coverage. Italian nationality verification remains a separate evidence-backed process; it must not be inferred from these parquet datasets. No claim of complete season coverage is made.
