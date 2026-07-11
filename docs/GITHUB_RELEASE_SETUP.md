# GitHub release setup

This checklist covers the authenticated GitHub settings that cannot be stored in the repository itself.

## Automated path

Install and authenticate the GitHub CLI:

```bash
brew install gh
gh auth login
```

Then run from the repository root:

```bash
./scripts/publish_github_release.sh
```

The script is idempotent. It verifies a clean worktree and local tag, pushes `main` and `v0.1.0-alpha`, updates the repository description and topics, and creates the Pre-release only when it does not already exist.

## Branch protection

Open:

`Settings → Branches → Add branch protection rule`

Use branch name pattern `main` and enable:

- Require a pull request before merging.
- Require status checks to pass before merging.
- Require branches to be up to date before merging.
- Select both CI checks: `backend` and `frontend`.
- Do not allow bypassing the above settings.

For a solo portfolio repository, requiring one approving review can make routine maintenance awkward. Leave the approval count at zero initially, but keep pull requests and CI required.

## Repository profile

Confirm the About panel contains:

- Description: `Eval-first observability dashboard for report-generating LLM workflows.`
- Topics: `agentops`, `deepseek`, `fastapi`, `llm-evaluation`, `llm-observability`, `openai`, `prompt-engineering`, `react`.
- License: MIT.

Enable private vulnerability reporting under `Settings → Security → Code security and analysis`.

## Portfolio visibility

Pin `agent-lens` on the GitHub profile and use `docs/PORTFOLIO.md` for resume, interview, launch-post, and demo copy.
