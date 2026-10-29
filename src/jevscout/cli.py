"""Command-line adapter for local run submission, collection and inspection."""

import argparse
import asyncio
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
    create.add_argument("--allow-local", action="store_true",
                        help="explicitly allow loopback fixture origins, not private networks")

    show = actions.add_parser("show", help="show one run")
    show.add_argument("run_id")
    actions.add_parser("list", help="list runs")
    execute = actions.add_parser("execute", help="collect and extract a pending run locally")
    execute.add_argument("run_id")
    execute.add_argument("--approve", action="store_true",
                         help="assert explicit user approval through the calling host")
    for action in ("pages", "results", "extract", "report"):
        command = actions.add_parser(action, help=f"{action} for a saved run")
        command.add_argument("run_id")
    artifact = actions.add_parser("artifact", help="read saved page evidence")
    artifact.add_argument("run_id")
    artifact.add_argument("--ref", required=True)
    return parser


def _emit(payload: object) -> None:
    json.dump(payload, sys.stdout, ensure_ascii=False, sort_keys=True)
    sys.stdout.write("\n")


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
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
                allow_local=args.allow_local,
            )
            record = store.create(spec)
            logger.debug("run request persisted run_id=%s", record.id)
            _emit(record.to_dict())
        elif args.action == "show":
            record = store.get(args.run_id)
            logger.debug("run inspected run_id=%s", record.id)
            _emit(record.to_dict())
        elif args.action == "list":
            records = store.list_runs()
            logger.debug("runs listed count=%d", len(records))
            _emit([record.to_dict() for record in records])
        elif args.action == "execute":
            from .application import execute_run
            record = asyncio.run(execute_run(store, args.run_id, approved=args.approve))
            _emit(record.to_dict())
            return 0 if record.status == "completed" else 1
        elif args.action == "pages":
            _emit(store.list_pages(args.run_id))
        elif args.action == "results":
            _emit(store.list_results(args.run_id))
        elif args.action == "extract":
            from .application import extract_run
            _emit(extract_run(store, args.run_id))
        elif args.action == "report":
            _emit(store.read_execution(args.run_id))
        elif args.action == "artifact":
            _emit({"html": store.read_artifact(args.run_id, args.ref)})
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
    except ImportError:
        logger.error("collection dependencies unavailable; install jevscout with the [crawl] extra")
        return 1
    except RuntimeError:
        logger.error("operation unavailable: approval, pending status or exclusive access required")
        return 2
    except (KeyboardInterrupt, asyncio.CancelledError):
        logger.warning("operation cancelled")
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
