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
COPY backend/pyproject.toml backend/uv.lock* ./
RUN uv sync --frozen --no-dev --no-editable 2>/dev/null || uv sync --no-dev

# ── Stage 3: Final image ──
FROM python:3.12-slim

# Install nginx and node (for Next.js standalone)
RUN apt-get update && apt-get install -y --no-install-recommends \
    nginx \
    curl \
    && curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Backend
WORKDIR /app/backend
COPY --from=backend-builder /app/.venv ./.venv
COPY backend/ .

# Frontend (standalone)
WORKDIR /app/frontend
COPY --from=frontend-builder /app/.next/standalone ./
COPY --from=frontend-builder /app/.next/static ./.next/static
COPY --from=frontend-builder /app/public ./public

# Nginx config
COPY nginx.docker.conf /etc/nginx/sites-enabled/default

# Startup script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 3000

ENV PORT=3000
ENV HOSTNAME=0.0.0.0

ENTRYPOINT ["/entrypoint.sh"]
