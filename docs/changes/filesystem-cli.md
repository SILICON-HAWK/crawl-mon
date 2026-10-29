# Filesystem CLI slice

## Behavior

Added `jevscout runs create`, `jevscout runs show`, and `jevscout runs list`. Create accepts repeatable seed URLs and page, depth, and timeout limits, then persists a `pending` request. The CLI does not start a worker or imply approval or live collection. Successful commands emit JSON on stdout; operational errors go to stderr with a nonzero exit status. Debug logging reports command outcomes and run IDs without including seed URLs, credentials, bodies, or exception details.

## Files

- `src/jevscout/cli.py`: argparse entry point backed by `RunSpec` and `FileRunStore`.
- `tests/test_cli.py`: subprocess coverage against a real temporary filesystem store.
- `docs/changes/filesystem-cli.md`: this implementation note.

## Checks

- Initial RED: `PYTHONPATH=src python3 -m unittest discover -s tests -p test_cli.py` failed in all three tests before the CLI existed (`jevscout.cli` could not be imported).
- Malformed-record RED: after adding a subprocess case that overwrote a valid `run.json` with `{}`, show and list failed because a missing field raised an uncaught `KeyError`.
- GREEN: the same command passed all four tests after handling that corruption (`Ran 4 tests ... OK`).

Coverage includes create in one process followed by show/list in separate processes, literal persisted spec and pending status, invalid page limits, credential URL rejection without echoing the URL, invalid run ID handling, and malformed stored records in show/list without traceback. No broader suite or live-source check was run for this bounded slice.

## Limitations and outstanding work

The filesystem store is single-writer and the CLI only records and inspects requests. No approval workflow, worker, crawler, source access, or collection execution is implemented here. Storage and malformed-data failures use concise generic errors; debug mode intentionally does not print exception details.
