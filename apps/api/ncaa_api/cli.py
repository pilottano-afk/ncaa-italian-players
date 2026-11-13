"""Command-line entry point for staging the current NCAA season."""
import argparse
import json

from ncaa_api.ingestion import DEFAULT_BOOTSTRAP_DATASETS, stage_bootstrap_data


def main() -> None:
    parser = argparse.ArgumentParser(description="Stage NCAA 2026-27 SportsDataverse datasets.")
    parser.add_argument(
        "--datasets",
        nargs="+",
        choices=sorted(
            {
                "schedule", "team_rosters", "rosters", "team_ids", "pbp",
                "player_box", "team_box", "lineups", "matchup_stints",
                "possessions", "shots",
            }
        ),
        default=list(DEFAULT_BOOTSTRAP_DATASETS),
        help="Dataset families to download. Defaults to schedule, rosters, player_box.",
    )
    parser.add_argument("--output", default="data/staging/2027")
    args = parser.parse_args()
    manifest = stage_bootstrap_data(args.output, tuple(args.datasets))
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
