#!/usr/bin/env bash
# scripts/agent_handoff_commit.sh
# ------------------------------------------------------------
# Automates the mini‑commit workflow after an AGENT HAND‑OFF.
# ------------------------------------------------------------
# 1. Adds updated Project_Summary_Updates.md (and any other
#    staged/working tree changes).
# 2. Creates a commit with a standard message:
#       "agent‑handoff: <UTC‑timestamp>"
#    Optionally appends a user‑supplied message.
# 3. Prompts whether to push to the default remote.
#
# Usage:
#   bash scripts/agent_handoff_commit.sh [optional extra msg]
#
# Example:
#   bash scripts/agent_handoff_commit.sh "dashboard fixes"
# ------------------------------------------------------------
set -euo pipefail

# Ensure we are in repo root regardless of invocation path
SCRIPT_DIR="$(cd "${BASH_SOURCE[0]%/*}" && pwd)"
cd "$SCRIPT_DIR/.."

# Verify git identity is configured
if ! git config user.name >/dev/null 2>&1 || [[ -z "$(git config user.name)" ]]; then
  read -rp "Git user.name not set. Enter a name to use for commits in this repo: " GIT_NAME
  git config user.name "$GIT_NAME"
fi

if ! git config user.email >/dev/null 2>&1 || [[ -z "$(git config user.email)" ]]; then
  read -rp "Git user.email not set. Enter an email to use for commits in this repo: " GIT_EMAIL
  git config user.email "$GIT_EMAIL"
fi

# Build commit message
TIMESTAMP="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
BASE_MSG="agent-handoff: $TIMESTAMP"
EXTRA_MSG="${*:-}"
COMMIT_MSG="$BASE_MSG${EXTRA_MSG:+ - $EXTRA_MSG}"

# Stage files – always include the summary file
if [[ -f Project_Summary_Updates.md ]]; then
  git add Project_Summary_Updates.md
fi
# Stage any other modified files (non‑deleted)
# Users can adjust this to be more selective if desired.
git add -u

# Abort if nothing to commit
if git diff --cached --quiet; then
  echo "Nothing to commit. Exiting."
  exit 0
fi

# Create commit
git commit -m "$COMMIT_MSG"
echo "✔ Commit created: $COMMIT_MSG"

echo "------------------------------------------------------------"
read -rp "Push commit to origin? [y/N]: " PUSH
if [[ "$PUSH" =~ ^[Yy]$ ]]; then
  git push
fi 