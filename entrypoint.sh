#!/bin/sh
set -e

# Start backend
cd /app/backend
uv run alembic upgrade head 2>/dev/null || true
uv run uvicorn maestro.app:app --host 127.0.0.1 --port 8000 &

# Start frontend
cd /app/frontend
PORT=3001 HOSTNAME=0.0.0.0 node server.js &

# Start nginx (foreground)
nginx -g "daemon off;"
