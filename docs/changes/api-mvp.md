# Local API MVP

Added a small FastAPI adapter for inspecting saved collection runs and submitting
an explicit pipeline request. `GET /api/runs` returns saved run records,
`GET /api/runs/{id}/results` returns extracted result objects, and the pipeline
routes list, start, and inspect in-process pipelines. Pipeline creation returns
`202 Accepted`; its POST is the explicit request that authorizes collection.

The API reads `JEVSCOUT_DATA_DIR` (default `data`) and uses the filesystem run
store. Pipeline status is held in memory by the pipeline manager, so it is lost
when the API process exits. The adapter does not accept arbitrary request
fields, does not expose profile data in pipeline responses, and returns generic
errors so source URLs and secrets are not reflected in error text.

Start it from `backend/` with:

```sh
uvicorn jevscout.interfaces.api:app --host 127.0.0.1 --port 8000
```

Keep the host bound to `127.0.0.1`; this MVP has no authentication and is for
local use. Pipeline submissions use the manager's conservative collection
limits and do not invoke an external scoring service.
