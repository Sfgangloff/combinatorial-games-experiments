#!/bin/bash
# One-shot setup: activate the project's tracked git hooks.
# Run once after cloning the repo, or any time .git/config gets reset.

set -e

cd "$(dirname "$0")/.."
git config core.hooksPath .githooks
chmod +x .githooks/pre-commit .githooks/pre-push 2>/dev/null || true
chmod +x .claude/hooks/*.sh 2>/dev/null || true

echo "Hooks activated:"
echo "  core.hooksPath -> $(git config --get core.hooksPath)"
ls -l .githooks/ | tail -n +2
