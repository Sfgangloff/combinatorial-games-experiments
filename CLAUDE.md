# Project context

This repo compares **MCP tool granularities** for an LLM (Claude
Code) solving Slitherlink puzzles, plus a procedural Slitherlink
generator with a formal difficulty grader. The research target is a
mid-tier archival publication. See `README.md` for the layout and
goals, and the dated `notes/` for current planning.

- Slitherlink rules: `rules.md`
- Grid parser/validator: `validate_grid.py`
- Prior experiments (file-based batch protocol): `legacy/` — read-only reference

There is **no prescribed solving protocol** in this repo. When
solving a puzzle, use the MCP tools available; when extending tools,
follow the design notes in `README.md`.

## Guardrails (enforced via `.claude/settings.json` + `.githooks/`)

These rules are *enforced*, not advisory — hooks and permission
denies will block violations. Working around them defeats the
purpose of the project policy.

- **`legacy/` is frozen reference.** Never edit anything there. The
  permission deny + the path-check hook will reject edits.
- **Subscription compute costs real money.** `harness.run_plan`
  without `--dry-run` is in the `ask` permission bucket *and* the
  bash hook requires `BUDGET_AUTHORIZED=1` in the session env. Never
  launch a window unless the user has explicitly asked in this turn
  — past authorization does **not** roll forward to a new turn.
- **`harness.run_plan --dry-run` is always free** and the right
  first move when planning a window.
- **Never `git push --force`, `git reset --hard`, `git commit
  --no-verify`, `git commit --amend`, `git rebase`, or `git clean
  -fd`.** All denied at the settings level.
- **Stay inside the repo root.** No reads/edits/writes outside
  `~/Desktop/claude-sudoku-experiments/`. The hook validates paths.
- **`harness/results/`, `.venv/`, `__pycache__/`, `.DS_Store`,
  `legacy/`** are never committed. The pre-commit git hook will
  reject these even if accidentally staged.
- **Commits must include the `Co-Authored-By: Claude Opus 4.7 (1M
  context)` line** — see existing log for the exact format.
- **Notify on findings.** When reporting an experimental result,
  gate verdict, aggregate statistic, or other paper-relevant
  observation, also fire a macOS notification via:
  `osascript -e 'display notification "<short summary>" with title
  "<context>"'`. Status updates / progress reports do NOT trigger a
  notification — only *findings*.

## Files Claude Code reads to know what to do

- `CLAUDE.md` (this file) — project context + guardrails (always loaded).
- `notes/2026-05-18_aaai_plan_and_meta_confound.md` — Phase-1 gate +
  meta-axis drop + running window log.
- `notes/2026-05-21_phase2_design.md` — Phase-2 design + G-CD theory.
- `notes/2026-05-21_paper_outline.md` — section plan + figures.
- `notes/2026-05-22_guardrails_design.md` — rationale behind the
  policy in this file + the hooks.
- Memories in `~/.claude/projects/.../memory/` — cross-session
  preferences (paper-target ceiling, meta-axis dropped, etc.).

## Hooks operating on Claude

| Event | Hook | Purpose |
| --- | --- | --- |
| PreToolUse: Edit/Write/MultiEdit | `.claude/hooks/check_path.sh` | Reject paths outside repo, legacy/, .git/, .venv/ |
| PreToolUse: Bash | `.claude/hooks/check_bash.sh` | Audit-log every command + block scope-escape + budget gate for run_plan |
| Stop | `.claude/hooks/end_summary.sh` | Append git status to audit log at end of turn |

## How to start Claude Code

```bash
cd ~/Desktop/claude-sudoku-experiments
claude                              # default permission mode (recommended)
# or, after intentional clone-setup:
bash scripts/setup_hooks.sh         # activates .githooks/ once
```

To authorize a real `harness.run_plan` window in the current session:

```bash
export BUDGET_AUTHORIZED=1
```

Unset (`unset BUDGET_AUTHORIZED`) when done. Better yet, do it in a
subshell that exits with the session.
