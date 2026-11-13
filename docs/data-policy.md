# Data policy and season boundary

## Hard season boundary

This application is scoped to NCAA men's basketball season 2026-27. Providers that encode the season by ending year must receive `2027`. Every imported game, roster snapshot, box score, play-by-play event, possession, lineup stint, and shot must be associated with this season key.

Historical seasons are out of scope. Ingestion must reject records whose season key is not 2027; it must not silently fall back to a provider's default season.

## Evidence and provenance

Every imported dataset must retain provider name, provider record ID, source URL or endpoint identifier where available, fetched timestamp (UTC), source update timestamp where available, and validation status. A missing value is not zero. Unavailable and unverified are separate states.

## Player identity

Italian nationality must be supported by an explicit reliable source and recorded with the evidence URL and verification status. RealGM may be used to discover candidate names, but is not sufficient by itself to establish Division I status or nationality. Confirm school, division, and current roster against official university/NCAA information where possible.

## Draft board

The 30 best overall NBA Draft 2027 prospects are a separate dataset and UI section. Nationality is unrestricted. Store ranking source, ranking date, and confidence; do not mix this list with the Italian NCAA player index.

## Advanced metrics

Calculate possessions, efficiency, on/off, lineup, shot profile, and percentile metrics only when their required source fields and coverage are adequate. Show denominator/sample size and suppress or flag unstable small samples. Percentiles must specify comparison population and update date.

## No synthetic data

Fixtures, players, box scores, and charts shown as real data must come from a verified provider response. Demo placeholders must be explicitly labelled as examples and must never be included in production analytics.
