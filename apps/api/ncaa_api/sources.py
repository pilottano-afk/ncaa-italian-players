"""Provider metadata and health states; never infer completeness from an empty response."""
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Literal

SourceState = Literal["not_configured", "configured", "reachable", "empty", "error", "partial"]


@dataclass(frozen=True)
class SourceHealth:
    source_id: str
    display_name: str
    state: SourceState
    checked_at: str
    season: int = 2027
    records_seen: int | None = None
    message: str | None = None
    documentation_url: str | None = None

    @classmethod
    def make(
        cls,
        source_id: str,
        display_name: str,
        state: SourceState,
        *,
        records_seen: int | None = None,
        message: str | None = None,
        documentation_url: str | None = None,
    ) -> "SourceHealth":
        return cls(
            source_id=source_id,
            display_name=display_name,
            state=state,
            checked_at=datetime.now(timezone.utc).isoformat(),
            records_seen=records_seen,
            message=message,
            documentation_url=documentation_url,
        )

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


SOURCE_CATALOG = [
    {
        "id": "sportsdataverse",
        "name": "SportsDataverse NCAA MBB",
        "role": "primary_candidate",
        "url": "https://github.com/sportsdataverse/ncaa-mbb-hoops-data",
        "upstream": "stats.ncaa.org",
        "datasets": [
            "schedule", "team_rosters", "rosters", "pbp", "player_box",
            "team_box", "lineups", "matchup_stints", "possessions", "shots",
        ],
    },
    {
        "id": "collegebasketballdata",
        "name": "CollegeBasketballData.com",
        "role": "secondary_crosscheck",
        "url": "https://api.collegebasketballdata.com/data-availability",
        "datasets": ["games", "rosters", "box_scores", "plays", "shooting", "lineups"],
    },
]
