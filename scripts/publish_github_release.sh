#!/usr/bin/env bash
set -euo pipefail

REPO="BrownieCoder/agent-lens"
TAG="v0.1.0-alpha"
DESCRIPTION="Eval-first observability dashboard for report-generating LLM workflows."
NOTES_FILE="docs/RELEASE_NOTES_v0.1.0-alpha.md"

if ! command -v gh >/dev/null 2>&1; then
  echo "GitHub CLI is required. Install it from https://cli.github.com/ and run: gh auth login"
  exit 1
fi

gh auth status

if [[ -n "$(git status --porcelain)" ]]; then
  echo "Working tree must be clean before publishing."
  exit 1
fi

if ! git rev-parse "$TAG" >/dev/null 2>&1; then
  echo "Missing local tag: $TAG"
  exit 1
fi

if [[ ! -f "$NOTES_FILE" ]]; then
  echo "Missing release notes: $NOTES_FILE"
  exit 1
fi

git push origin main
git push origin "$TAG"

gh repo edit "$REPO" \
  --description "$DESCRIPTION" \
  --enable-issues \
  --add-topic agentops \
  --add-topic deepseek \
  --add-topic fastapi \
  --add-topic llm-evaluation \
  --add-topic llm-observability \
  --add-topic openai \
  --add-topic prompt-engineering \
  --add-topic react

if gh release view "$TAG" --repo "$REPO" >/dev/null 2>&1; then
  echo "Release $TAG already exists; leaving it unchanged."
else
  gh release create "$TAG" \
    --repo "$REPO" \
    --title "Agent Lens v0.1.0-alpha" \
    --notes-file "$NOTES_FILE" \
    --prerelease
fi

echo "Published: https://github.com/$REPO/releases/tag/$TAG"
