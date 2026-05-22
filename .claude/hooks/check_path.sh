#!/bin/bash
# PreToolUse hook for Edit / Write / MultiEdit.
# Rejects writes to paths outside the project root or to forbidden subdirs.
# Input JSON arrives on stdin; we parse it with python3 (stdlib only).

set -e

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"
INPUT="$(cat)"

TARGET="$(printf '%s' "$INPUT" | /usr/bin/python3 -c \
    'import json,sys; d=json.load(sys.stdin); print(d.get("tool_input",{}).get("file_path",""))' 2>/dev/null)"

if [ -z "$TARGET" ]; then
    exit 0
fi

case "$TARGET" in
    /*) ABS="$TARGET" ;;
    *)  ABS="$PROJECT_DIR/$TARGET" ;;
esac

# Canonicalize via python (handles .. and symlinks portably).
ABS_CANON="$(/usr/bin/python3 -c "import os,sys; print(os.path.realpath(sys.argv[1]))" "$ABS")"
ROOT_CANON="$(/usr/bin/python3 -c "import os,sys; print(os.path.realpath(sys.argv[1]))" "$PROJECT_DIR")"

# Allow common temp paths the harness writes to.
case "$ABS_CANON" in
    /tmp/*|/private/tmp/*|/var/folders/*) exit 0 ;;
esac

# Must be inside project root.
case "$ABS_CANON" in
    "$ROOT_CANON"/*) ;;
    "$ROOT_CANON")   ;;
    *)
        echo "Blocked: $ABS_CANON is outside project root ($ROOT_CANON)." >&2
        exit 2
        ;;
esac

# Forbidden subtrees (belt-and-braces vs the settings.json deny list).
case "$ABS_CANON" in
    "$ROOT_CANON"/legacy/*)
        echo "Blocked: legacy/ is frozen reference. See CLAUDE.md." >&2
        exit 2
        ;;
    "$ROOT_CANON"/.git/*)
        echo "Blocked: .git/ internals must not be modified." >&2
        exit 2
        ;;
    "$ROOT_CANON"/.venv/*)
        echo "Blocked: .venv/ is managed by pip, do not edit." >&2
        exit 2
        ;;
esac

exit 0
