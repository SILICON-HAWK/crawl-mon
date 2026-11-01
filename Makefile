PYTHON ?= .venv/bin/python
UVICORN ?= .venv/bin/uvicorn
NPM ?= npm
BUILT_FRONTEND_DIR ?= frontend/dist-built
BUILT_HOST ?= 127.0.0.1
BUILT_PORT ?= 8081
DATA_DIR ?= data/live-trial

.PHONY: build-built deploy-built run-built

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
