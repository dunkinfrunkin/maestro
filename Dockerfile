# ── Stage 1: Build frontend ──
FROM node:22-alpine AS frontend-builder
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci
COPY frontend/ .
ENV NEXT_PUBLIC_API_URL=""
RUN npm run build

# ── Stage 2: Build backend deps ──
FROM python:3.12-slim AS backend-builder
WORKDIR /app
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
COPY backend/ .
RUN touch README.md && uv sync --frozen --no-dev 2>/dev/null || uv sync --no-dev

# ── Stage 3: Final image ──
FROM python:3.12-slim

# Install nginx and node
RUN apt-get update && apt-get install -y --no-install-recommends \
    nginx \
    curl \
    && curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

# Backend — copy venv and source
WORKDIR /app/backend
COPY --from=backend-builder /app/.venv ./.venv
COPY --from=backend-builder /app/ .

# Frontend — copy standalone build
WORKDIR /app/frontend
COPY --from=frontend-builder /app/.next/standalone ./
COPY --from=frontend-builder /app/.next/static ./.next/static
COPY --from=frontend-builder /app/public ./public

# Nginx config — use conf.d since sites-enabled may not exist
COPY nginx.docker.conf /etc/nginx/conf.d/maestro.conf
RUN rm -f /etc/nginx/sites-enabled/default /etc/nginx/conf.d/default.conf 2>/dev/null; true

# Startup script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 3000

ENV PORT=3000
ENV HOSTNAME=0.0.0.0

ENTRYPOINT ["/entrypoint.sh"]
