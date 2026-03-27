#!/bin/sh
set -e

# Start backend
cd /app/backend
.venv/bin/python -m alembic upgrade head 2>/dev/null || true
.venv/bin/uvicorn maestro.app:app --host 127.0.0.1 --port 8000 &

# Start frontend
cd /app/frontend
PORT=3001 HOSTNAME=0.0.0.0 node server.js &

# Wait for services to start
sleep 2

# Start nginx (foreground)
nginx -g "daemon off;"
