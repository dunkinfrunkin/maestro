FROM python:3.12-slim AS base

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Install dependencies
COPY pyproject.toml uv.lock* ./
RUN uv sync --frozen --no-dev --no-editable 2>/dev/null || uv sync --no-dev

# Copy application
COPY . .

# Run migrations then start server
CMD ["sh", "-c", "uv run alembic upgrade head 2>/dev/null; uv run uvicorn maestro.app:app --host 0.0.0.0 --port 8000"]
