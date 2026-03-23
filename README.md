# Maestro

> Inspired by [Symphony](https://github.com/openai/symphony), built for enterprise.

Maestro is an autonomous coding agent orchestration platform. It manages a pipeline of AI agents that implement, review, risk-assess, deploy, and monitor code changes — all triggered from your issue tracker.

**Currently under active development.**

## How It Works

```
Issue → Queued → Implement → Review ↔ (loop) → Risk Profile → Deploy → Monitor
```

1. **Implement** — An AI agent reads the issue, writes code, runs tests, creates a PR
2. **Review** — A review agent posts inline comments on specific lines of code
3. **Implement** (follow-up) — The implementation agent reads review comments, fixes issues, replies in the thread
4. **Review** (re-review) — Verifies fixes, resolves comment threads, approves when done
5. **Risk Profile** — Scores the PR across 7 risk dimensions, auto-approves low risk
6. **Deploy** — Merges the PR, monitors CI/CD pipeline
7. **Monitor** — Post-deployment health checks

Agents communicate through PR comment threads — just like human developers.

## Stack

- **Backend**: Python / FastAPI / PostgreSQL / SQLAlchemy
- **Frontend**: Next.js 15 / TypeScript / Tailwind CSS
- **Agents**: Claude Code CLI (configurable model per agent)
- **Trackers**: GitHub Issues, Linear
- **Auth**: Local email/password with JWT

## Features

- Workspaces and projects with role-based access (owner/member)
- GitHub and Linear issue tracker integrations
- 5 pipeline agents with configurable prompts and models
- Live activity streaming on task detail pages
- Inline PR code reviews with comment thread conversations
- Encrypted API key and token storage
- Plugin framework for custom enterprise agents

## Quick Start

```bash
# Start PostgreSQL
docker compose up -d

# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
uvicorn maestro.app:app --port 8000

# Frontend
cd frontend
npm install && npm run dev
```

Open http://localhost:3000, create an account, add a GitHub connection, and start orchestrating.

## License

MIT
