"""Season boundary helpers: this product only accepts NCAA season 2027 (2026-27)."""
from collections.abc import Iterable
from typing import Any

CURRENT_SEASON = 2027
CURRENT_SEASON_LABEL = "2026-27"


class SeasonBoundaryError(ValueError):
    """Raised when a provider record belongs to a season outside the product scope."""


def require_current_season(value: Any) -> int:
    """Parse a provider season and reject every season except 2027."""
    try:
        season = int(value)
    except (TypeError, ValueError) as exc:
        raise SeasonBoundaryError(f"Invalid or missing season value: {value!r}") from exc
    if season != CURRENT_SEASON:
        raise SeasonBoundaryError(
            f"Season {season} rejected: this app only stores {CURRENT_SEASON_LABEL}."
        )
    return season


def filter_current_season(records: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return only 2026-27 records; malformed and historical records are rejected."""
    accepted: list[dict[str, Any]] = []
    for record in records:
        require_current_season(record.get("season"))
        accepted.append(record)
    return accepted
