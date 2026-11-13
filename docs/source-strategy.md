# Data-source strategy (2026-27 only)

## Verified source characteristics

### SportsDataverse NCAA MBB

The upstream pipeline is based on parsed `stats.ncaa.org` data (not ESPN). Its published data model includes schedule, team rosters, player rosters, play-by-play, player/team box scores, lineups, matchup stints, possessions and shots. The project should consume only the 2027 season partition and must inspect actual per-dataset coverage before enabling a feature.

Reference: https://github.com/sportsdataverse/ncaa-mbb-hoops-data

### CollegeBasketballData.com

The API uses bearer authentication. Its season key is the ending year, so `season=2027` means 2026-27. The provider documents season availability for games, rosters, player/team stats, play-by-play, shooting, substitutions and lineups, but explicitly warns that listed availability does not guarantee complete coverage for every team, game or field. Free API keys currently have a monthly request quota; the full Team Metrics and Shooting Profiles require a higher tier.

References:
- https://api.collegebasketballdata.com/getting-started
- https://api.collegebasketballdata.com/data-availability

## Integration policy

1. SportsDataverse is the leading candidate for detailed event and lineup data.
2. CollegeBasketballData is a cross-check and potential fallback, not an assumed complete replacement.
3. A provider is not marked healthy merely because its website responds. We must validate a real 2026-27 payload and required fields.
4. Empty response, missing field, zero statistic and unavailable endpoint are distinct states.
5. Every imported row must retain provider identity, source record ID where available, fetched timestamp and validation result.
6. All ingestion functions enforce season 2027. No historical backfill is permitted in this application.
7. Nationality and Division I status require explicit evidence; name matching alone is not enough.

## Current integration status

The API client and season boundary are implemented. No API key is stored in Git, and no provider payload has yet been imported. The UI must continue to show source coverage as unverified until a live response is checked.
