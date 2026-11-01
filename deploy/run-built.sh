#!/bin/sh
set -eu

uvicorn_bin=${1:-.venv/bin/uvicorn}
frontend_dir=${JEVSCOUT_FRONTEND_DIR:-frontend/dist-built}
host=${BUILT_HOST:-0.0.0.0}
port=${BUILT_PORT:-8081}

if [ ! -x "$uvicorn_bin" ]; then
  printf 'Uvicorn executable not found or not executable: %s\n' "$uvicorn_bin" >&2
  exit 1
fi
if [ ! -f "$frontend_dir/index.html" ]; then
  printf 'Built frontend not found at %s; run make build-built first.\n' "$frontend_dir" >&2
  exit 1
fi

# Bind-probe before launching so an existing server is never replaced or signaled.
if ! python3 - "$host" "$port" <<'PY'
import socket
import sys

host, port = sys.argv[1], int(sys.argv[2])
sock = socket.socket()
try:
    sock.bind((host, port))
except OSError:
    print(f"Cannot start built JevScout: {host}:{port} is unavailable; choose another BUILT_PORT.", file=sys.stderr)
    raise SystemExit(1)
finally:
    sock.close()
PY
then
  exit 1
fi

export JEVSCOUT_FRONTEND_DIR="$frontend_dir"
exec "$uvicorn_bin" jevscout.interfaces.production:app --app-dir backend/src \
  --host "$host" --port "$port"
