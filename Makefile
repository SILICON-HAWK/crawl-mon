PYTHON ?= .venv/bin/python
UVICORN ?= .venv/bin/uvicorn
NPM ?= npm
BUILT_FRONTEND_DIR ?= frontend/dist-built
BUILT_HOST ?= 0.0.0.0
BUILT_PORT ?= 8081
DATA_DIR ?= data/live-trial

.PHONY: build-built deploy-built run-built dev-api dev-web dev dev-and-built fetch-parallel

TIME ?= 2h
CONCURRENCY ?= 4
INDIA_ONLY ?= true

# Run parallel long-running job fetching across all 8 ATS providers and Wellfound.
# Usage: make fetch-parallel TIME=2h [CONCURRENCY=4] [INDIA_ONLY=true|false] [DATA_DIR=data/live-trial]
fetch-parallel:
	PYTHONPATH=backend/src $(PYTHON) -m jevscout.application.parallel_fetch \
	  --data-dir $(DATA_DIR) --duration $(TIME) --concurrency $(CONCURRENCY) \
	  $$( [ "$(INDIA_ONLY)" = "false" ] && echo "--all-locations" || echo "--india-only" ) $(ARGS) --approve


# Create a production frontend snapshot kept separate from Vite development.
build-built:
	cd frontend && npm run build -- --outDir ../$(BUILT_FRONTEND_DIR)

# Build the frontend, then serve it with the production API adapter.
deploy-built: build-built
	JEVSCOUT_FRONTEND_DIR=$(BUILT_FRONTEND_DIR) JEVSCOUT_DATA_DIR=$(DATA_DIR) \
	  BUILT_HOST=$(BUILT_HOST) BUILT_PORT=$(BUILT_PORT) \
	  ./deploy/run-built.sh $(UVICORN)

# Run an already-built snapshot without rebuilding it.
run-built:
	JEVSCOUT_FRONTEND_DIR=$(BUILT_FRONTEND_DIR) JEVSCOUT_DATA_DIR=$(DATA_DIR) \
	  BUILT_HOST=$(BUILT_HOST) BUILT_PORT=$(BUILT_PORT) \
	  ./deploy/run-built.sh $(UVICORN)

DEV_API_PORT ?= 8000

# Development API (auto-reload) on loopback.
dev-api:
	JEVSCOUT_DATA_DIR=$(DATA_DIR) $(UVICORN) jevscout.interfaces.api:app \
	  --app-dir backend/src --reload --host 127.0.0.1 --port $(DEV_API_PORT)

# Vite dev server (5173); proxies /api to the dev API.
dev-web:
	cd frontend && JEVSCOUT_API_ORIGIN=http://127.0.0.1:$(DEV_API_PORT) $(NPM) run dev

# Dev API + Vite together; Ctrl-C stops both.
dev:
	@trap 'kill 0' INT TERM EXIT; $(MAKE) dev-api & $(MAKE) dev-web & wait

# Prebuilt production app (8081) and the dev app together; Ctrl-C stops all.
dev-and-built: build-built
	@trap 'kill 0' INT TERM EXIT; $(MAKE) run-built & $(MAKE) dev-api & $(MAKE) dev-web & wait
