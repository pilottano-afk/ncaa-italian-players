"""Command-line entry points for NCAA data staging, auditing and raw import."""
import argparse
import json
import os

from ncaa_api.audit import audit_staged_data
from ncaa_api.ingestion import DEFAULT_BOOTSTRAP_DATASETS, stage_bootstrap_data
from ncaa_api.raw_import import import_staged_raw


def stage_main() -> None:
    parser = argparse.ArgumentParser(description="Stage NCAA 2026-27 SportsDataverse datasets.")
    parser.add_argument(
        "--datasets", nargs="+",
        choices=sorted({
            "schedule", "team_rosters", "rosters", "team_ids", "pbp",
            "player_box", "team_box", "lineups", "matchup_stints",
            "possessions", "shots",
        }),
        default=list(DEFAULT_BOOTSTRAP_DATASETS),
        help="Dataset families to download. Defaults to schedule, rosters, player_box.",
    )
    parser.add_argument("--output", default="data/staging/2027")
    args = parser.parse_args()
    manifest = stage_bootstrap_data(args.output, tuple(args.datasets))
    print(json.dumps(manifest, indent=2))


def audit_main() -> None:
    parser = argparse.ArgumentParser(
        description="Audit staged NCAA Parquet nulls, candidate keys and joins."
    )
    parser.add_argument("--input", default="data/staging/2027")
    parser.add_argument("--output", default="data/staging/2027/quality-audit.json")
    args = parser.parse_args()
    report = audit_staged_data(args.input, args.output)
    print(json.dumps(report, indent=2))


def import_raw_main() -> None:
    parser = argparse.ArgumentParser(
        description="Import verified NCAA 2026-27 source rows into PostgreSQL JSONB."
    )
    parser.add_argument("--input", default="data/staging/2027")
    parser.add_argument(
        "--database-url",
        default=os.environ.get("DATABASE_URL"),
        help="PostgreSQL URL; defaults to the DATABASE_URL environment variable.",
    )
    parser.add_argument("--batch-size", type=int, default=500)
    args = parser.parse_args()
    if not args.database_url:
        parser.error("Provide --database-url or set DATABASE_URL.")
    report = import_staged_raw(args.input, args.database_url, batch_size=args.batch_size)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    stage_main()
