#!/bin/bash
# Build paper/main.pdf from main.tex + references.bib.
# Runs pdflatex+biber via latexmk; quiet by default.
#
# Usage: bash paper/build.sh           (from repo root)
#    or  bash build.sh                 (from paper/)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if ! command -v latexmk >/dev/null 2>&1; then
    echo "build.sh: latexmk not found on PATH. Install TeX Live 2024+." >&2
    exit 1
fi

latexmk -pdf -interaction=nonstopmode -halt-on-error main >/dev/null

if [ -f main.pdf ]; then
    # Page count from the log: 'Output written on main.pdf (N pages, ...'
    pages=$(grep -oE 'Output written on main\.pdf \([0-9]+ pages' main.log 2>/dev/null \
              | tail -1 | grep -oE '[0-9]+' || echo '?')
    bytes=$(stat -f%z main.pdf 2>/dev/null || stat -c%s main.pdf 2>/dev/null)
    printf 'paper/main.pdf built (%s pages, %s bytes)\n' "$pages" "$bytes"
else
    echo "build.sh: latexmk completed but main.pdf not found." >&2
    exit 1
fi
