---
sidebar_position: 5
title: .agents/
sidebar_label: .agents/
---

# .agents/ Directory

Maestro is built on top of agentic coding systems like Claude Code, Codex, and whatever comes next. These platforms are backed by Anthropic, OpenAI, and others investing billions into making AI agents better at writing code. Maestro doesn't compete with them - it orchestrates them.

But these agents have a fundamental limitation: they can read your code, but they can't infer your team's decisions. Why you chose Fernet over AES. Why all API routes need auth middleware. Why you never use VARCHAR. Why deploys go to staging before prod. That knowledge lives in people's heads, and when an agent doesn't have it, it writes code that technically works but doesn't belong.

The `.agents/` directory solves this. It's a set of markdown files that live in your repository root, each one a structured briefing for a specific concern. Agents read these files before every task. The better you fill them out, the better the agents perform.

## Why markdown

Every major agentic platform (Claude Code, Codex, Cursor, Copilot) reads markdown natively. By using plain markdown files in the repo, Maestro's context layer works with any current or future agent platform without custom integrations. As these platforms improve, the `.agents/` files automatically become more useful because smarter agents extract more value from the same context.

## Creating the directory

```bash
maestro repo init
```

This scaffolds 11 template files. Each has placeholder comments that you replace with specifics about your codebase.

## The files

Each file exists for a reason. They're organized by concern, not by agent, because multiple agents read the same file for different purposes.

| File | Purpose |
|---|---|
| [SPECIFICATION.md](specification) | What to build and why |
| [ARCHITECTURE.md](architecture) | How the system is structured |
| [DATABASE.md](database) | Schema, migrations, data conventions |
| [API_CONTRACTS.md](api-contracts) | Endpoint shapes and error handling |
| [STYLE_GUIDE.md](style-guide) | Code conventions agents must follow |
| [SECURITY.md](security) | Auth, secrets, and vulnerability prevention |
| [COMPLIANCE.md](compliance) | Regulatory and data handling rules |
| [TEST_STRATEGY.md](test-strategy) | What to test and how |
| [RUNBOOK.md](runbook) | Operational procedures and incident response |
| [DEPLOY.md](deploy) | Deployment process and environments |
| [MONITORING.md](monitoring) | Metrics, alerts, and post-deploy checks |

## Keeping it current

Stale context is worse than no context. It leads agents to make confident but wrong assumptions. Update `.agents/` files when:

- You add a new service or major module
- Authentication or authorization patterns change
- Database conventions change (new ORM, new migration tool)
- Deployment infrastructure changes
- You discover agents repeatedly making the same mistake (add the correction to the relevant file)
