# Docker

The image uses Python 3.12 slim, installs JevScout with the `crawl` and `postgres` extras, and runs as UID/GID 10001. It has no server process: the image entry point is the `jevscout` CLI, so each container invocation performs one command and exits. Set `JEVSCOUT_DATABASE_URL` to select PostgreSQL storage.

## Filesystem mode

For current filesystem-backed use, mount a persistent directory at `/data`. The image creates that directory owned by the non-root runtime user, so a newly created named volume is writable. A host bind mount must also be writable by UID 10001 (or use an appropriate host ACL). Only one writer should use a filesystem data directory.

```sh
docker build -t jevscout .
docker run --rm -v jevscout_data:/data jevscout runs list
docker run --rm -v jevscout_data:/data jevscout runs create \
  --seed https://example.com/careers --max-pages 10 --max-depth 1
```

Global options such as `--data-dir` go before the command. `/data` is the default target in the container. The `JEVSCOUT_DATA_DIR` environment setting is part of the container contract; the current CLI also accepts `--data-dir /data` explicitly.

## Compose with PostgreSQL

`compose.yaml` defines PostgreSQL 17 with persistent storage and a readiness check. It does not publish the database port to the host. The app is a one-shot CLI service on the same private Compose network; it waits for a healthy database and mounts its own persistent `/data` volume. The database hostname in the connection URL is `db`, never `localhost` from inside the app container.

Start the database, then initialize the application schema and issue CLI commands:

```sh
docker compose build app
docker compose up -d db
docker compose run --rm app db init
docker compose run --rm app runs list
docker compose run --rm app runs create \
  --seed https://example.com/careers --max-pages 10 --max-depth 1
```

`db init` creates schema version 1 explicitly and is safe to repeat. Existing filesystem data is not imported. The PostgreSQL backend stores evidence and metadata in the database; `/data` holds engine workspaces. This is synchronous storage integration, without a background queue or crash-resume guarantee. Compose's database credentials are configurable with `POSTGRES_DB`, `POSTGRES_USER`, and `POSTGRES_PASSWORD`; the documented local default password (`jevscout_dev`) is for development only and must be replaced for any shared deployment. These values are interpolated into the local connection URL. Do not commit a populated `.env` file.

Compose services are not started as a long-running JevScout web application. Use `docker compose run --rm app <jevscout arguments>` for each CLI operation. `docker compose down` retains the named volumes; add `-v` only when intentionally deleting persisted database and application data.

## Proxy CA trust

When package installation needs the managed network's CA, pass the combined CA bundle as a BuildKit secret. The Dockerfile uses it only during pip installation and does not store it in an image layer. In environments without an interception CA, an ordinary portable build needs no secret:

```sh
docker build -t jevscout .
```

With a custom bundle:

```sh
docker build --secret id=proxy_ca,src="$CODEX_PROXY_CERT" -t jevscout .
```

Compose reads the same source from `CODEX_PROXY_CERT`, defaulting to `/etc/ssl/certs/ca-certificates.crt`. Set it when building/running in an environment whose combined CA bundle is elsewhere:

```sh
CODEX_PROXY_CERT=/path/to/combined-ca.pem docker compose build
```

The Compose secret is mounted read-only into the one-shot app process and exposed as `SSL_CERT_FILE` and `REQUESTS_CA_BUNDLE` for outbound HTTPS trust. Recreate the app container after changing proxy or CA settings. Keep certificate verification enabled. Container DNS and proxy reachability depend on the Docker network and runtime's configured proxy; an application container cannot use its own `localhost` to reach a host or sibling service.

## Integration checks

The separate test image includes fixtures and tests; the runtime image does not.
Use a disposable Compose project so integration runs do not populate your app database:

```sh
docker compose -p jevscout-test build test
docker compose -p jevscout-test run --rm test discover -s tests/db -t . -v
docker compose -p jevscout-test run --rm test
```

The full suite includes regression coverage for filesystem scoring locks, India
location filtering, and application-URL identity, alongside PostgreSQL and
controlled-fixture crawler checks.
Test runs add records; remove the disposable project's volumes only when finished
with its test data. No automatic filesystem-to-database migration is provided.
