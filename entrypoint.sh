#!/bin/bash
set -e

export PATH="/app/engine/.venv/bin:$PATH"

# If arguments are passed, delegate to the Python CLI
# e.g. "maestro worker --concurrency 3" or "maestro serve"
if [ $# -gt 0 ]; then
    cd /app/engine
    python -m alembic upgrade head 2>/dev/null || true
    exec maestro "$@"
fi

# Default: run the full stack (API + frontend + nginx)
cd /app/engine
python -m alembic upgrade head 2>/dev/null || true
python -m uvicorn maestro.app:app --host 127.0.0.1 --port 8000 &

cd /app/frontend
PORT=3001 HOSTNAME=0.0.0.0 node server.js &

sleep 2

nginx -g "daemon off;"
