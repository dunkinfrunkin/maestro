---
tracker:
  kind: linear
  api_key: $LINEAR_API_KEY
  project_slug: my-project
  active_states:
    - Todo
    - In Progress
  terminal_states:
    - Done
    - Canceled
polling:
  interval_ms: 30000
workspace:
  root: /tmp/maestro-workspaces
agent:
  max_concurrent_agents: 4
  max_retry_backoff_ms: 320000
codex:
  command: echo '{"jsonrpc":"2.0","id":1,"result":{"thread_id":"t1"}}' && echo '{"method":"turn/completed","params":{}}'
  read_timeout_ms: 5000
  turn_timeout_ms: 3600000
  stall_timeout_ms: 300000
---

You are an autonomous coding agent working on issue {{ issue.identifier }}: {{ issue.title }}.

## Issue Details
- **Description**: {{ issue.description }}
- **Priority**: {{ issue.priority }}
- **Labels**: {{ issue.labels }}

{% if attempt %}
This is retry attempt #{{ attempt }}. Review previous work and continue from where you left off.
{% endif %}

## Instructions
1. Read the issue description carefully
2. Implement the requested changes
3. Write tests for your changes
4. Ensure all existing tests pass
5. Create a pull request with your changes
