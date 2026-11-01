# Built local deployment command

Added `make deploy-built` to build a dedicated Vite production snapshot and serve it through the existing production FastAPI adapter. `make build-built` only builds; `make run-built` serves an existing snapshot. The default address is loopback port 8081, separate from Vite development on 5173 and the stable app on 8080. Host, port, snapshot path, data path, and Uvicorn executable are configurable via Make variables.

The server uses the existing filesystem run store and user-assets path, so saved pipeline records and profile-scoped actions remain shared with the local app. Pipeline jobs submitted through the API run through the existing in-process `PipelineManager`; the independent scheduled feed refresh remains the existing CLI worker and is not started by this command. This is a local single-process deployment, not an installed service or restart-managed daemon.

The launch script checks that the snapshot and Uvicorn executable exist and probes the requested bind address before starting. An occupied address exits without signaling or replacing its current process. A bind race after the check is still possible, in which case Uvicorn reports the bind error. Do not run multiple app processes against the same filesystem data root concurrently.

Checks: `make -n deploy-built` rendered the expected build and launch commands. `make build-built` completed successfully. An isolated `make run-built BUILT_PORT=18081 DATA_DIR=/tmp/jevscout-built-smoke` served `/`, `/jobs`, and `/api/jobs` with HTTP 200; a second start on the same port failed safely. The temporary server was then stopped. This did not exercise real feed collection or model calls.
