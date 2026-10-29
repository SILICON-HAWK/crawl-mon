"""Command-line adapter for pending run submission and inspection."""

import argparse
import json
import logging
import sys
from pathlib import Path

from .models import RunSpec
from .storage import FileRunStore


logger = logging.getLogger("jevscout.cli")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="jevscout")
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument("--debug", action="store_true", help="enable diagnostic logging")
    commands = parser.add_subparsers(dest="area", required=True)

    runs = commands.add_parser("runs", help="submit or inspect runs")
    actions = runs.add_subparsers(dest="action", required=True)

    create = actions.add_parser("create", help="persist a pending run request")
    create.add_argument("--seed", action="append", required=True, metavar="URL")
    create.add_argument("--max-pages", type=int, default=10)
    create.add_argument("--max-depth", type=int, default=1)
    create.add_argument("--timeout-seconds", type=int, default=60)

    show = actions.add_parser("show", help="show one run")
    show.add_argument("run_id")
    actions.add_parser("list", help="list runs")
    return parser


def _emit(payload: object) -> None:
    json.dump(payload, sys.stdout, ensure_ascii=False, sort_keys=True)
    sys.stdout.write("\n")


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.WARNING,
        stream=sys.stderr,
        format="%(levelname)s: %(message)s",
    )

    try:
        store = FileRunStore(args.data_dir)
        if args.area != "runs":
            parser.error("unsupported command")
        if args.action == "create":
            spec = RunSpec(
                seed_urls=args.seed,
                max_pages=args.max_pages,
                max_depth=args.max_depth,
                timeout_seconds=args.timeout_seconds,
            )
            record = store.create(spec)
            logger.debug("run request persisted run_id=%s", record.id)
            _emit(record.to_dict())
        elif args.action == "show":
            record = store.get(args.run_id)
            logger.debug("run inspected run_id=%s", record.id)
            _emit(record.to_dict())
        else:
            records = store.list_runs()
            logger.debug("runs listed count=%d", len(records))
            _emit([record.to_dict() for record in records])
        return 0
    except (json.JSONDecodeError, KeyError):
        logger.error("stored run data is corrupt")
        return 1
    except (ValueError, TypeError):
        logger.error("invalid run request or identifier")
        return 2
    except OSError:
        logger.error("unable to access run storage")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
