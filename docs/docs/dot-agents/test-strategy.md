---
sidebar_position: 8
title: TEST_STRATEGY.md
---

# TEST_STRATEGY.md

**Read by:** QA

## Why it exists

When the Implementation Agent writes code, it runs the existing test suite. But it doesn't know if it should also write new tests, what kind, or where to put them. Without a testing strategy, agents either skip tests entirely or write the wrong kind (unit tests where you need integration tests, or vice versa).

The QA Agent uses this file to validate that test coverage is adequate for the change.

## What to include

- **Framework** - Testing tools and how to run them
- **Test types** - Unit, integration, E2E - what each covers and where they live
- **What to test vs. what not to test** - Concrete guidance, not philosophy
- **Fixtures and helpers** - Common test utilities agents should use

## Example

```markdown
# Test Strategy

## Framework
Backend: pytest with pytest-asyncio
Frontend: vitest
E2E: Playwright (not yet set up)

## Running Tests
pytest backend/tests/
npm test --prefix frontend

## Test Types
| Type | Location | When to write |
|---|---|---|
| Unit | tests/unit/ | Pure functions, data transformations |
| Integration | tests/integration/ | DB queries, API endpoints |
| E2E | tests/e2e/ | Critical user flows (when Playwright is set up) |

## What to Test
- Every new API endpoint needs at least one happy path test
- Every DB model change needs a migration test
- Agent dispatch logic needs integration tests with a real DB

## What NOT to Test
- Don't mock the database (we got burned by mock/prod divergence)
- Don't test third-party libraries
- Don't write E2E tests for admin-only features

## Fixtures
- conftest.py has async_session, test_user, test_workspace
- Use factory functions in tests/factories.py for models
```
