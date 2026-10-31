# Local frontend MVP

From the repository root, install the backend web and crawler extras and the frontend dependencies:

```sh
.venv/bin/python -m pip install -e './backend[crawl,web]'
cd frontend && npm ci
```

Start the API from the repository root in one terminal. The data directory defaults to `data/`; set `JEVSCOUT_DATA_DIR=data/live-trial` to view the earlier test runs.

```sh
JEVSCOUT_DATA_DIR=data/live-trial .venv/bin/uvicorn jevscout.interfaces.api:app --host 127.0.0.1 --port 8000
```

Start Vite in another terminal:

```sh
cd frontend
npm run dev
```

Open the local address Vite prints. Enter one or more public feed URLs and a candidate profile, then explicitly start a pipeline. It runs one pipeline at a time with up to five sources, a maximum of five pages per source and a 120-second per-source timeout. The numeric rank is a simple local keyword heuristic, not an AI judgment. It does not read your résumé automatically or call OpenRouter. Existing runs and their saved results are available in the dashboard.

Pipeline progress and rankings are held in memory and disappear when the API restarts; collected run records and evidence remain in the chosen data directory. There is no background recovery or authentication. Run the API and development server on loopback only. Never put API keys or résumé contents in seed URLs. See [the MVP plan](frontend-mvp-plan.md) for the data flow and later review.

## Built app and development app

Build a separate static snapshot and serve it together with its own API process:

```sh
cd frontend
npm ci
npm run build -- --outDir dist-stable
cd ..
JEVSCOUT_DATA_DIR=data/live-trial JEVSCOUT_USER_ASSETS_DIR=user-assets \
  .venv/bin/uvicorn jevscout.interfaces.production:app --host 100.70.228.53 --port 8080
```

Replace the host address with this machine's current Tailscale IP (`tailscale ip -4`). The built snapshot is independent of the Vite development server on port 5173; it changes only on a subsequent build to `dist-stable`. Restart the stable API process after backend changes. The two API processes share filesystem data but each has its own in-memory pipeline status. The application has no login, so anyone with network access can inspect profile data and initiate operations. Processes started this way are not registered as persistent services.
