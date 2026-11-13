"""Downloader for the official SportsDataverse NCAA MBB release assets."""
from pathlib import Path

import httpx

from ncaa_api.season import CURRENT_SEASON, require_current_season


DATASETS = frozenset(
    {
        "schedule",
        "team_rosters",
        "rosters",
        "pbp",
        "player_box",
        "team_box",
        "lineups",
        "matchup_stints",
        "possessions",
        "shots",
        "team_ids",
    }
)
RELEASE_ROOT = "https://github.com/sportsdataverse/sportsdataverse-data/releases/download"


class SportsDataverseClient:
    """Fetch a single season partition from a named release.

    This client downloads the published asset only. It does not claim the
    partition is complete; coverage must be checked after inspecting its rows.
    """

    def __init__(self, timeout: float = 90.0) -> None:
        self.timeout = timeout

    @staticmethod
    def dataset_url(dataset: str, season: int = CURRENT_SEASON) -> str:
        require_current_season(season)
        if dataset not in DATASETS:
            raise ValueError(f"Unsupported NCAA MBB dataset: {dataset}")
        tag = f"ncaa_mbb_{dataset}"
        filename = f"ncaa_mbb_{dataset}_{season}.parquet"
        return f"{RELEASE_ROOT}/{tag}/{filename}"

    def download(self, dataset: str, destination: str | Path, season: int = CURRENT_SEASON) -> Path:
        url = self.dataset_url(dataset, season)
        target = Path(destination)
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_name(target.name + ".part")

        try:
            with httpx.stream("GET", url, follow_redirects=True, timeout=self.timeout) as response:
                response.raise_for_status()
                with temporary.open("wb") as output:
                    for chunk in response.iter_bytes():
                        output.write(chunk)
            self.validate_parquet(temporary)
            temporary.replace(target)
        except Exception:
            temporary.unlink(missing_ok=True)
            raise
        return target

    @staticmethod
    def validate_parquet(path: str | Path) -> None:
        """Check the Parquet file signature before accepting the download."""
        file_path = Path(path)
        with file_path.open("rb") as source:
            header = source.read(4)
            source.seek(-4, 2)
            footer = source.read(4)
        if header != b"PAR1" or footer != b"PAR1":
            raise ValueError(f"Downloaded asset is not a valid Parquet file: {file_path}")
