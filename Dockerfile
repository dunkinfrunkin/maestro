# ── Stage 1: Build frontend (always on native platform, no emulation) ──
FROM --platform=$BUILDPLATFORM node:22-alpine AS frontend-builder
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci
COPY frontend/ .
ENV NEXT_PUBLIC_API_URL=""
RUN npm run build

# ── Stage 2: Build engine deps ──
FROM python:3.12-slim AS engine-builder
WORKDIR /app
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
COPY engine/ .
RUN touch README.md && uv sync --frozen --no-dev 2>/dev/null || uv sync --no-dev

# ── Stage 3: Final image ──
FROM python:3.12-slim

# Install nginx, node, git
RUN apt-get update && apt-get install -y --no-install-recommends \
    nginx \
    curl \
    git \
    && curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

# Install CLI agent tools
RUN npm install -g @anthropic-ai/claude-code @openai/codex 2>/dev/null || \
    npm install -g @anthropic-ai/claude-code || true

# Backend — copy venv and source
WORKDIR /app/engine
COPY --from=engine-builder /app/.venv ./.venv
COPY --from=engine-builder /app/ .

# Frontend — copy standalone build
WORKDIR /app/frontend
COPY --from=frontend-builder /app/.next/standalone ./
COPY --from=frontend-builder /app/.next/static ./.next/static
COPY --from=frontend-builder /app/public ./public

# Nginx config
COPY nginx.docker.conf /etc/nginx/conf.d/maestro.conf
RUN rm -f /etc/nginx/conf.d/default.conf 2>/dev/null; \
    mkdir -p /etc/nginx/sites-enabled; \
    rm -f /etc/nginx/sites-enabled/default 2>/dev/null; \
    true

# Startup script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 3000

ENV PORT=3000
ENV HOSTNAME=0.0.0.0

ENTRYPOINT ["/entrypoint.sh"]
