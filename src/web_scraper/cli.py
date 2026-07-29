"""Command-line interface for configured scraping jobs."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from web_scraper.config import load_config
from web_scraper.pipeline import run


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Configuration-driven, responsible web scraping")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command, mode in (("scrape", "static"), ("api", "api")):
        subparser = subparsers.add_parser(command, help=f"Run a {mode} extraction configuration")
        subparser.add_argument("--config", required=True, help="Path to YAML configuration")
        subparser.add_argument(
            "--output", required=True, help="Destination .csv, .xlsx, or .xlsm file"
        )
        subparser.add_argument(
            "--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"]
        )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    logging.basicConfig(level=getattr(logging, args.log_level), format="%(levelname)s %(message)s")
    config = load_config(args.config)
    accepted_modes = {"static", "javascript"} if args.command == "scrape" else {"api"}
    if config.mode not in accepted_modes:
        expected = ", ".join(sorted(accepted_modes))
        raise SystemExit(f"'{args.command}' requires a configuration with mode: {expected}")
    _, summary = run(config, args.output)
    print(f"Exported {Path(args.output)}")
    print("Data quality summary:")
    for metric, value in summary.as_dict().items():
        print(f"  {metric.replace('_', ' ')}: {value}")


if __name__ == "__main__":
    main()
