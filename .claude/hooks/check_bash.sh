#!/bin/bash
# PreToolUse hook for Bash.
# Lightweight audit logger + sanity check for shell scope escape + budget gate.
# Input JSON arrives on stdin; parsed with python3 (stdlib only).

set -e

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"
AUDIT_LOG="$PROJECT_DIR/.claude/audit.log"

INPUT="$(cat)"
CMD="$(printf '%s' "$INPUT" | /usr/bin/python3 -c \
    'import json,sys; d=json.load(sys.stdin); print(d.get("tool_input",{}).get("command",""))' 2>/dev/null)"

if [ -z "$CMD" ]; then
    exit 0
fi

# Audit log: timestamp + cwd + truncated command (single line).
TRUNC="$(printf '%s' "$CMD" | head -c 500 | tr '\n' ' ')"
printf '[%s] cwd=%s cmd=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$(pwd)" "$TRUNC" >> "$AUDIT_LOG"

# Block obvious scope-escape patterns the settings.json prefix list can't catch.
case "$CMD" in
    *"cd /"*|*"cd ~"*)
        echo "Blocked: shell command contains cd outside project root." >&2
        exit 2
        ;;
esac

# Budget gate: harness.run_plan without --dry-run requires explicit auth.
case "$CMD" in
    *"harness.run_plan"*)
        case "$CMD" in
            *"--dry-run"*) ;;
            *)
                if [ "${BUDGET_AUTHORIZED:-0}" != "1" ]; then
                    echo "Blocked: harness.run_plan without --dry-run burns subscription compute. Set BUDGET_AUTHORIZED=1 in this session, or run with --dry-run first." >&2
                    exit 2
                fi
                ;;
        esac
        ;;
esac

exit 0
