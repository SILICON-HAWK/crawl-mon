# Test suites

Run from the repository root. Tests use public application/storage/CLI boundaries,
controlled crawler fixtures, and mocked external decision-provider responses.

| Folder | Coverage |
| --- | --- |
| `core` | Models, run scope, application operations, JSON-LD extraction |
| `crawler` | Crawlee/network restrictions and collection CLI lifecycle |
| `cli` | CLI validation, persistence and offline scoring |
| `storage` | Filesystem artifacts, results and process locking |
| `db` | Real PostgreSQL persistence, locking and CLI integration |
| `feeds` | Six ATS adapters, registry and saved-feed integration |
| `scoring` | Decision clients, rubrics, scoring and regressions |
| `util` | Location, description quality and token harvesting |
| `docker` | Non-root packaged CLI, dependencies and writable volume |
| `support`, `fixtures` | Shared test server and saved input data |

Full local discovery:

```sh
PYTHONPATH=backend/src python3 -m unittest discover -s backend/tests -t backend -v
```

Select a subsystem by changing the start directory:

```sh
PYTHONPATH=backend/src python3 -m unittest discover -s backend/tests/core -t backend -v
PYTHONPATH=backend/src python3 -m unittest discover -s backend/tests/crawler -t backend -v
```

Crawlee checks require `.[crawl]`; database checks require `.[postgres]` and
`JEVSCOUT_TEST_DATABASE_URL` pointing to a disposable initialized database
(the suite initializes schema itself). Docker packaging checks run only in the
test image. Local success with skips does not verify those integrations.

For every subsystem, with dependencies installed and a real database:

```sh
docker compose -f deploy/compose.yaml build test
docker compose -f deploy/compose.yaml run --rm test
docker compose -f deploy/compose.yaml run --rm test discover -s tests/db -t . -v
docker compose -f deploy/compose.yaml run --rm test discover -s backend/tests/crawler -t backend -v
```

Use a disposable Compose project (`-p jevscout-test`) to isolate test records.
The Docker suite should report no skips. It exercises controlled local sites,
not live ATS sites or the OpenRouter API. Test failure expectations must not be
weakened merely to make the suite pass; review whether the code or test is wrong.
