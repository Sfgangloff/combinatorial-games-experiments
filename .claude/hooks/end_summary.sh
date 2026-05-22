#!/bin/bash
# Stop hook — runs when Claude finishes a turn.
# Appends a one-line git status summary to the audit log so you can scan
# the log and immediately see which turns left the tree dirty.

set -e

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"
AUDIT_LOG="$PROJECT_DIR/.claude/audit.log"

cd "$PROJECT_DIR"

DIRTY="$(git status --short 2>/dev/null | wc -l | tr -d ' ')"
BRANCH="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo '?')"

printf '[%s] STOP branch=%s dirty_files=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$BRANCH" "$DIRTY" >> "$AUDIT_LOG"

exit 0
