---
sidebar_position: 9
title: Contributing
---

# Contributing

We welcome contributions to Maestro. Whether it's a bug fix, a new feature, documentation improvement, or a new integration, here's how to get involved.

## Process

1. **Open an issue first** for any non-trivial change - describe the problem or feature
2. **Fork and clone** the repository
3. **Set up** the development environment with `make setup`
4. **Create a branch** for your work
5. **Open a PR** referencing the issue (e.g., "Fixes #123")
6. **Wait for review** - maintainers will review and provide feedback

Small fixes like typos or one-line corrections can go straight to a PR without an issue.

## Setup

```bash
git clone https://github.com/YOUR_USERNAME/maestro.git
cd maestro
make setup    # Start postgres + install all deps
maestro app   # Verify everything works
```

See [Local Development](/docs/installation/local-dev) for full setup details.

## What to work on

Check [open issues](https://github.com/dunkinfrunkin/maestro/issues) for things that need help. Issues labeled `good first issue` are a great starting point.

Areas where contributions are especially welcome:

- **Integrations** - new tracker or code host integrations
- **Agents** - improvements to agent prompts and behavior
- **Documentation** - corrections, new guides, examples
- **Tests** - expanding test coverage
- **UI** - dashboard improvements and new features

## PR requirements

- Reference an issue in the PR body
- One concern per PR - keep it focused
- Existing tests must pass
- New features should include tests
- Follow existing code patterns

## Commit messages

Use conventional commit prefixes:

- `fix:` - bug fixes
- `feat:` - new features
- `docs:` - documentation changes
- `refactor:` - code restructuring
- `test:` - test additions or fixes
- `chore:` - maintenance tasks

## Running tests

```bash
cd engine
uv run pytest
```

## Code of conduct

Be respectful and constructive. We're building something together.
