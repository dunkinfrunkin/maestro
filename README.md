# Maestro

A Python/FastAPI + Next.js implementation of the [Symphony specification](https://github.com/openai/symphony/blob/main/SPEC.md) — an orchestration daemon that manages coding agents to execute work from issue trackers.

## Architecture

```
maestro/
├── backend/          # Python FastAPI backend
│   └── maestro/
│       ├── api/          # HTTP endpoints
│       ├── agent/        # Agent runner (subprocess protocol)
│       ├── config/       # Config layer + WORKFLOW.md parser
│       ├── orchestrator/ # Polling, state machine, dispatch
│       ├── tracker/      # Issue tracker adapters (Linear)
│       ├── workspace/    # Per-issue workspace manager
│       ├── models.py     # Core domain models
│       ├── app.py        # FastAPI application
│       └── cli.py        # CLI entry point
└── frontend/         # Next.js dashboard
```

## Quick Start

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
maestro --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## License

Apache-2.0
