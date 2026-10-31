# JevScout frontend

Small Svelte/Vite dashboard for the local JevScout API.

```sh
cd frontend
npm install
npm run dev
```

Open the loopback URL printed by Vite. The development server proxies `/api` to `http://127.0.0.1:8000`; set `JEVSCOUT_API_ORIGIN` to change the API origin. The dev and preview servers bind to loopback by default.

The dashboard loads runs and pipeline status, lets you inspect a run's jobs and a pipeline's ranked results, and starts a pipeline after the user supplies one or more seed URLs and a candidate profile JSON object. It sends `POST /api/pipeline` with `{ "seed_urls": [...], "profile": {...} }`. Pipeline and run lists refresh every eight seconds. The profile editor starts with an editable software engineer example; change it to fit the search.

To run the API separately from the repository root, use the backend environment and launch `uvicorn jevscout.interfaces.api:app --host 127.0.0.1 --port 8000` with `PYTHONPATH=backend/src`.
