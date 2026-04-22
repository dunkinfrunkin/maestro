# Maestro

Autonomous coding agent orchestration for engineering teams.

Maestro is built on top of agentic coding systems like Claude Code, Codex, and whatever comes next. It doesn't compete with these platforms - it orchestrates them. It provides the pipeline, quality gates, and operational guardrails that turn raw agent capability into reliable engineering output.

## How it works

Issues come from your tracker. Agents take over from there.

```
Issue synced -> Implementing -> In Review -> Approved -> Deploying -> Done
```

| Agent | What it does |
|---|---|
| **Implementation** | Reads your codebase, writes code, runs tests, opens a PR |
| **Review** | Posts inline comments on specific lines, requests changes or approves |
| **Risk Profile** | Scores the PR across 7 dimensions, auto-approves low risk |
| **Deploy** | Verifies CI checks, merges via squash |
| **Monitor** | Watches metrics and logs for 15 minutes post-deploy |

Agents communicate through PR comment threads - the same workflow as human developers.

## Install

```bash
brew install dunkinfrunkin/tap/maestro
```

## Quick start

```bash
# Generate config
maestro init

# Start the app + worker
maestro app      # Terminal 1
maestro worker   # Terminal 2
```

Dashboard at [localhost:3000](http://localhost:3000). Connect your GitHub/GitLab/Linear/Jira in **Settings > Connections**, create an issue in your tracker, assign a repo, and move it to **Implement**.

## Integrations

| Platform | Role | What Maestro does |
|---|---|---|
| **GitHub** | Codebase + Tracker | Opens PRs, posts inline reviews, reads issues, checks CI |
| **GitLab** | Codebase + Tracker | Opens MRs, posts discussions, reads issues, checks pipelines |
| **Linear** | Tracker | Syncs issues, updates status |
| **Jira** | Tracker | Syncs issues from Cloud or Server, updates status |

## Project structure

```
maestro/
  engine/     # Python platform - API, worker, agents, orchestrator
  ui/         # Next.js dashboard
  cli/        # Go CLI (Homebrew distribution)
  docs/       # Docusaurus documentation site
```

## Development

```bash
git clone https://github.com/dunkinfrunkin/maestro.git
cd maestro
make setup    # Start postgres + install all deps
maestro app   # Start API + dashboard
```

See the full [local development guide](https://maestro.frankchan.dev/docs/installation/local-dev) for details.

## CLI

| Command | What it does |
|---|---|
| `maestro app` | Start full stack (API + dashboard) |
| `maestro serve` | Start API server only |
| `maestro worker` | Start agent worker process |
| `maestro init` | Generate `~/.maestro/config.yaml` |
| `maestro repo init` | Scaffold `.agents/` context templates for a repo |

## Documentation

Full docs at [maestro.frankchan.dev](https://maestro.frankchan.dev):

- [Getting Started](https://maestro.frankchan.dev/docs/getting-started)
- [Concepts](https://maestro.frankchan.dev/docs/concepts)
- [Lifecycle](https://maestro.frankchan.dev/docs/pipeline)
- [Agents](https://maestro.frankchan.dev/docs/agents)
- [Integrations](https://maestro.frankchan.dev/docs/integrations)
- [Configuration](https://maestro.frankchan.dev/docs/configuration)
- [Authentication](https://maestro.frankchan.dev/docs/authentication)

## License

MIT
