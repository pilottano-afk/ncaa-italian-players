# NCAA 2026-27 normalized data model — proposal

This is the next layer above `ncaa_raw_rows`. It is a design contract, not a claim that normalized tables have already been created or populated.

## Design rules

1. Raw JSONB rows remain immutable and are the source of truth.
2. Every normalized row must retain `artifact_sha256` and `source_row_number` so it can be traced back to a provider record.
3. The only accepted season is `2027` (2026-27).
4. Null identifiers remain unresolved source records; do not manufacture player or team IDs.
5. Candidate keys from the quality audit become database constraints only after row-level semantics are confirmed.
6. Italian nationality is an independent evidence-backed classification, not a property inferred from a player name or NCAA roster row.

## Proposed entity groups

| Table | Primary purpose | Source family | Key policy |
|---|---|---|---|
| `ncaa_games` | Game date, home/away teams and score | schedule | `contest_id` is a candidate key; enforce only after normalized-load checks |
| `ncaa_teams` | NCAA team identity and conference | team_ids | `(season, id)` is a candidate key |
| `ncaa_players` | Player identity and canonical display name | team_rosters, rosters, player_box | Keep unresolved rows outside the entity table |
| `ncaa_roster_memberships` | Player-team-season roster, class, position, height and jersey | team_rosters | Candidate key `(season, team_id, player_id)` |
| `ncaa_player_game_stats` | Traditional and advanced player box score fields | player_box | Candidate key `(contest_id, player_id)` only for complete IDs |
| `ncaa_team_game_stats` | Team possessions, ratings, shooting, rebounding and turnovers | team_box | Candidate key `(contest_id, team_ncaa_team_id)` only for complete IDs |
| `ncaa_pbp_events` | Event sequence, clock, participants and lineup slots | pbp | Preserve provider event order and nullable participant IDs |
| `ncaa_possessions` | Possession-level event and lineup context | possessions | Candidate key `(contest_id, poss_num)` |
| `ncaa_lineups` | Five-player lineup and stint metrics | lineups | Preserve provider lineup identifiers; do not assume they are globally unique |
| `ncaa_matchup_stints` | Home/away lineup matchups over a game stint | matchup_stints | Candidate key `(contest_id, game_stint_num)` |
| `ncaa_shots` | Shot coordinates, zone, type, shooter and outcome | shots | Keep shots with unresolved shooter IDs; coordinates remain source coordinates |

## Unresolved identity handling

The current audit found missing identifiers in meaningful portions of the source:
- 2,685 `player_box` rows have no `player_id`.
- 197 `team_box` rows have no `team_ncaa_team_id`.
- 12,065 `shots` rows have no `shooter_player_id`.

These records should remain available in raw storage and in a normalized unresolved-record view. They must not be discarded merely because they cannot yet be joined to a player or team entity.

## Italian-player verification

Create a separate `ncaa_player_nationality_evidence` relation with:
- season and player identifier (nullable while unresolved)
- nationality claim (e.g. Italy)
- evidence type (official university bio, national-team record, direct federation source)
- source URL and source title
- short evidence note
- verification status (`verified`, `needs_review`, `rejected`)
- checked timestamp

A player's inclusion in the Italian directory requires at least one accepted primary-source evidence record. Conflicting or incomplete evidence must remain visible as a review state.

## Draft 2027 prospects

Keep the top-30 Draft prospect snapshot separate from NCAA player identity and nationality evidence. A prospect can be any nationality and may not be playing NCAA basketball. Store ranking position, player name, team/league, source, snapshot date and review status. Never merge prospect rank with NCAA player performance rank.

## Derived analytics

Derived metrics should be materialized only after the normalized facts pass checks. Store the formula/version and the input availability alongside each metric. Missing denominators must yield null/unavailable, not zero. Percentiles must be calculated against a defined comparison population and the same metric definition for all included players or teams.

## Load sequence

1. Verify artifact and season manifest.
2. Preserve source rows in `ncaa_raw_rows`.
3. Normalize teams and games.
4. Normalize roster memberships and player identities.
5. Load player/team box scores.
6. Load play-by-play, possessions, lineups, matchup stints and shots.
7. Run row-level relationship and reconciliation checks.
8. Add verified Italian-player evidence.
9. Calculate advanced metrics and percentiles.
10. Expose only records that pass the relevant verification gates.

No step in this proposal asserts that the 2026-27 schedule or any competition coverage is complete.
