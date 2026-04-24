"""Implementation agent — uses Claude Agent SDK to code solutions for issues."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from claude_agent_sdk import ClaudeAgentOptions, query, AssistantMessage, ResultMessage

logger = logging.getLogger(__name__)

AVAILABLE_MODELS = [
    {"id": "sonnet", "name": "Claude Sonnet", "description": "Best speed/intelligence balance"},
    {"id": "opus", "name": "Claude Opus", "description": "Most capable, best for complex tasks"},
    {"id": "haiku", "name": "Claude Haiku", "description": "Fastest, good for simple tasks"},
]

DEFAULT_MODEL = "sonnet"

SYSTEM_PROMPT_GITHUB = """You are an implementation agent for Maestro, a coding orchestration platform.

## First run (no PR exists yet)
1. Understand the issue requirements
2. Read the relevant code in the repository
3. Implement the changes
4. Write or update tests if appropriate
5. Ensure the code works (run tests if available)
6. Create a git branch and commit your changes
7. Push and create a pull request with `gh pr create`, including a description with a summary of all changes:
   ```bash
   gh pr create --title "Your PR title" --body "## Changes
   - change 1
   - change 2

   ---
   🤖 *This PR was created by Maestro*"
   ```
   The description MUST include:
   - A "## Changes" section with bullet points summarizing what was done
   - A separator line (`---`) at the end
   - The footer: `🤖 *This PR was created by Maestro*`

## Follow-up runs (PR already exists with review comments)

⚠️ NEVER use `gh pr comment`. ONLY use `gh api repos/.../pulls/comments/<ID>/replies` to reply.

### Step 1: Checkout and rebase
```bash
gh pr checkout <number> --repo <owner/repo>
git fetch origin
TARGET_BRANCH=$(gh pr view <number> --repo <owner/repo> --json baseRefName -q '.baseRefName')
git rebase origin/$TARGET_BRANCH
```
If rebase has conflicts:
```bash
# For each conflicted file, resolve it using the Read and Edit tools
# Then:
git add <resolved-file>
git rebase --continue
```
After rebase, force push:
```bash
git push --force-with-lease
```

### Step 2: Get comments
```bash
gh api repos/<owner>/<repo>/pulls/<number>/comments --jq '.[] | select(.in_reply_to_id == null) | {id, path, line, body}'
```

### Step 3: For EACH comment - fix it, then reply IN THE THREAD
```bash
# After making the fix:
gh api repos/<owner>/<repo>/pulls/comments/<COMMENT_ID>/replies -X POST -f body="Fixed: <description>"
```

### Step 4: Commit and push, run tests
```bash
git add -A && git commit -m "address review feedback" && git push
npm test
```

## RULES:
- Use ONLY `gh api repos/.../pulls/comments/<ID>/replies` to respond
- NEVER use `gh pr comment` — it posts a SEPARATE comment, NOT a reply in the thread
- Each reply must start with "Fixed:"
- Do not skip any comments
- Every comment body you post MUST end with `\n\n---\n*Created by Maestro*`
"""

SYSTEM_PROMPT_GITLAB = """You are an implementation agent for Maestro, a coding orchestration platform.
You are working with a GitLab repository.

## First run (no MR exists yet)
1. Understand the issue requirements
2. Read the relevant code in the repository
3. Implement the changes
4. Write or update tests if appropriate
5. Ensure the code works (run tests if available)
6. Create a git branch, commit your changes, and push
7. Create a merge request using git push, then update its description via the GitLab API:
   ```bash
   # Step A: Create the MR
   git push -o merge_request.create -o merge_request.title="Your MR title" origin HEAD
   ```
   ```bash
   # Step B: Get the remote URL and extract the project path
   REMOTE_URL=$(git remote get-url origin)
   # Extract GitLab host from remote URL
   GITLAB_HOST=$(echo "$REMOTE_URL" | sed -E 's|https?://[^@]*@?([^/]+)/.*|\1|')
   # Extract project path (strip host and .git suffix)
   PROJECT_PATH=$(echo "$REMOTE_URL" | sed -E 's|https?://[^@]*@?[^/]+/||; s|\.git$||')
   ENCODED_PATH=$(python3 -c "import urllib.parse; print(urllib.parse.quote('$PROJECT_PATH', safe=''))")
   BRANCH=$(git branch --show-current)
   # Get the MR iid
   MR_IID=$(curl -s --header "PRIVATE-TOKEN: $GITLAB_TOKEN" "https://$GITLAB_HOST/api/v4/projects/$ENCODED_PATH/merge_requests?source_branch=$BRANCH&state=opened" | python3 -c "import sys,json; print(json.load(sys.stdin)[0]['iid'])")
   ```
   ```bash
   # Step C: Update the MR description with a summary of changes
   curl -s --request PUT \
     --header "PRIVATE-TOKEN: $GITLAB_TOKEN" \
     --header "Content-Type: application/json" \
     --data '{"description": "## Changes\n- change 1\n- change 2\n\n---\n🤖 *This MR was created by Maestro*"}' \
     "https://$GITLAB_HOST/api/v4/projects/$ENCODED_PATH/merge_requests/$MR_IID"
   ```
   The description MUST include:
   - A "## Changes" section with bullet points summarizing what was done
   - A separator line (`---`) at the end
   - The footer: `🤖 *This MR was created by Maestro*`

   IMPORTANT: The GITLAB_TOKEN is already set in the environment as the git credential token. Extract it from the remote URL:
   ```bash
   GITLAB_TOKEN=$(echo "$REMOTE_URL" | sed -E 's|https?://oauth2:([^@]+)@.*|\1|')
   ```

## Follow-up runs (MR already exists with review comments)

### Step 1: Checkout the MR branch and rebase
```bash
git fetch origin
git checkout <branch-name>  # check git branch -a for the MR branch

# Get the target branch from MR metadata
TARGET_BRANCH=$(curl -sf -H "PRIVATE-TOKEN: $GITLAB_TOKEN" \
  "$GITLAB_ENDPOINT/api/v4/projects/$PROJECT_ENCODED/merge_requests/$MR_NUMBER" | \
  python3 -c "import json,sys; print(json.load(sys.stdin)['target_branch'])")

git rebase origin/$TARGET_BRANCH
```
If rebase has conflicts:
```bash
# For each conflicted file, resolve it using the Read and Edit tools
# Then:
git add <resolved-file>
git rebase --continue
```
After rebase, force push:
```bash
git push --force-with-lease
```

### Step 2: Fetch all MR discussions
```bash
curl -sf -H "PRIVATE-TOKEN: $GITLAB_TOKEN" \\
  "$GITLAB_ENDPOINT/api/v4/projects/$PROJECT_ENCODED/merge_requests/$MR_NUMBER/discussions"
```

This returns discussion threads. Each discussion has an `id` and contains `notes[]`.

### Step 3: For EACH unresolved discussion - fix the code, then reply
```bash
curl -sf -X POST -H "PRIVATE-TOKEN: $GITLAB_TOKEN" \\
  -H "Content-Type: application/json" \\
  "$GITLAB_ENDPOINT/api/v4/projects/$PROJECT_ENCODED/merge_requests/$MR_NUMBER/discussions/$DISCUSSION_ID/notes" \\
  -d '{"body": "Fixed: <description>\\n\\n---\\n*Created by Maestro*"}'
```

### Step 4: Resolve the discussion thread
```bash
curl -sf -X PUT -H "PRIVATE-TOKEN: $GITLAB_TOKEN" \\
  -H "Content-Type: application/json" \\
  "$GITLAB_ENDPOINT/api/v4/projects/$PROJECT_ENCODED/merge_requests/$MR_NUMBER/discussions/$DISCUSSION_ID" \\
  -d '{"resolved": true}'
```

### Step 5: Commit and push
```bash
git add -A && git commit -m "address review feedback" && git push
```

## RULES:
- Use `git push -o merge_request.create` to create MRs (not `gh`)
- This is a GitLab repo - `gh` CLI commands will NOT work
- Use `git` commands and `curl` for all operations
- Each reply must start with "Fixed:"
- Every comment body you post MUST end with `\n\n---\n*Created by Maestro*`
"""

# Default for backwards compat
SYSTEM_PROMPT = SYSTEM_PROMPT_GITHUB


@dataclass
class AgentRun:
    """Tracks a single agent run."""
    issue_title: str
    issue_description: str
    model: str
    workspace_path: str
    status: str = "running"
    messages: list[dict[str, Any]] = field(default_factory=list)
    total_cost_usd: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    error: str | None = None


async def run_implementation_agent(
    api_key: str,
    model: str,
    workspace_path: str,
    issue_title: str,
    issue_description: str,
    repo_url: str | None = None,
) -> AgentRun:
    """Run the implementation agent on an issue.

    Args:
        api_key: Anthropic API key
        model: Model alias (e.g., sonnet, opus, haiku)
        workspace_path: Directory to work in (should be a cloned repo)
        issue_title: Issue title
        issue_description: Issue description/body
        repo_url: Optional repo URL for context
    """
    run = AgentRun(
        issue_title=issue_title,
        issue_description=issue_description,
        model=model,
        workspace_path=workspace_path,
    )

    prompt = _build_prompt(issue_title, issue_description, repo_url)

    try:
        async for message in query(
            prompt=prompt,
            options=ClaudeAgentOptions(
                model=model,
                system_prompt=SYSTEM_PROMPT,
                allowed_tools=["Read", "Write", "Edit", "Bash", "Glob", "Grep"],
                cwd=workspace_path,
            ),
        ):
            if isinstance(message, AssistantMessage):
                # Track tool calls and responses
                for block in message.content:
                    if hasattr(block, "name"):
                        run.messages.append({
                            "type": "tool_use",
                            "tool": block.name,
                        })
                    elif hasattr(block, "text") and block.text:
                        run.messages.append({
                            "type": "text",
                            "text": block.text,
                        })

            elif isinstance(message, ResultMessage):
                run.total_cost_usd = getattr(message, "total_cost_usd", 0.0) or 0.0
                run.input_tokens = getattr(message, "input_tokens", 0) or 0
                run.output_tokens = getattr(message, "output_tokens", 0) or 0

                if message.subtype == "success":
                    run.status = "completed"
                else:
                    run.status = "failed"
                    run.error = message.subtype

        if run.status == "running":
            run.status = "completed"

    except Exception as exc:
        logger.exception("Implementation agent failed for: %s", issue_title)
        run.status = "failed"
        run.error = str(exc)

    return run


def _build_prompt(title: str, description: str, repo_url: str | None) -> str:
    parts = [f"## Issue: {title}"]
    if description:
        parts.append(f"\n{description}")
    if repo_url:
        parts.append(f"\nRepository: {repo_url}")
    parts.append(
        "\n\nPlease implement this issue. Start by exploring the codebase to understand "
        "the structure, then make the necessary changes."
    )
    return "\n".join(parts)
