# Guardrails design — what the policy enforces and why

**Date:** 2026-05-22. **Status:** active policy (in force on `main`).

## Problem statement

User wants to leave Claude Code running unattended on this project
without giving authorizations constantly, while preventing it from
(a) breaking the project, (b) making the repo messy, (c) escaping
the project's scope, or (d) burning subscription compute
unintentionally. Settings + hooks should be checked into the repo so
they survive clones and machine moves.

## Layered defense

Four layers, deepest-to-shallowest:

| Layer | Lives in | Enforces |
| --- | --- | --- |
| 1. Claude Code permissions (allow/deny/ask) | `.claude/settings.json` (tracked) | What Claude is allowed to *ask* the system to do |
| 2. Claude Code hooks | `.claude/hooks/*.sh` (tracked) | Path scope, audit logging, budget gate |
| 3. Git hooks | `.githooks/*` (tracked, activated via `core.hooksPath`) | What ends up in the repo / on origin |
| 4. CLAUDE.md guardrails section | `CLAUDE.md` (tracked) | What Claude *understands* the policy to be |

Layers 1+2 catch Claude's actions before they happen. Layer 3 catches
anything that slips through (or that the human does directly). Layer
4 ensures Claude isn't surprised by being blocked — it knows the
rules and writes code that respects them.

## Specific guardrails and their rationale

### `.claude/settings.json` permissions

**Posture:** pragmatic (broad allow + targeted deny). User decision.

Routine operations are in `allow` so Claude doesn't prompt. The
`allow` list includes the Slitherlink MCP tool families, the harness
analysis commands (`aggregate_phase1`, `visualize`), the generator,
test runs, read-only shell (`ls`, `cat`, `grep`, `find`, etc.), and
the standard git workflow up to and including `git push origin`.

`deny` blocks the genuinely-irreversible operations: any form of
force push, hard reset, `--amend`, `--no-verify`, `git rebase`, `git
clean -fd`, `rm -rf`, `sudo`, edits to `legacy/` or `.git/` or
`/etc/` or `~/.ssh/`. These never have a legitimate Claude use case
in this project.

Anything not in `allow` and not in `deny` falls to **ask** by
default. The big one in `ask`: `harness.run_plan` *without*
`--dry-run`. That's the budget gate — every cost-burning window
launch requires an explicit per-turn approval.

### Hooks

- **`check_path.sh`** (PreToolUse on Edit/Write/MultiEdit). Resolves
  the target path to an absolute canonical form, checks it's under
  the project root, blocks if it's under `legacy/`, `.git/`, or
  `.venv/`. Allows `/tmp/claude-*` and `/var/folders/*` for Claude's
  own temp area.

- **`check_bash.sh`** (PreToolUse on Bash). Two jobs:
  1. *Audit log.* Every Bash command + cwd appended to
     `.claude/audit.log` (gitignored). Lets you scan a day's worth
     of Claude actions in a single tail.
  2. *Budget gate.* If the command contains `harness.run_plan` and
     not `--dry-run`, requires `BUDGET_AUTHORIZED=1` in the env.
     Defense-in-depth alongside the settings.json `ask` rule. Note:
     hooks see the command *before* the permission prompt fires, so
     this blocks even if the user clicks "approve" by mistake.

- **`end_summary.sh`** (Stop). One line to the audit log: branch
  name + count of dirty files. Lets you scan for turns that left the
  tree messy.

### Git hooks via `.githooks/` (tracked, activated by `core.hooksPath`)

Activated once per clone via `bash scripts/setup_hooks.sh`. Two hooks:

- **`pre-commit`**:
  1. Rejects staged files in `harness/results/`, `legacy/`, `.venv/`,
     `__pycache__/`, `.pyc`, `.DS_Store`. Backstops the gitignore in
     case something accidentally got `git add -A`-ed.
  2. If `core/generator.py` is in the staged set, runs the
     `--selftest` and rejects on failure.
  3. AST-parses every staged `.py` under `harness/`, `core/`,
     `servers/`; rejects syntax errors.

- **`pre-push`**:
  1. Rejects deletion of `refs/heads/main` on the remote.
  2. Rejects non-fast-forward push to `main` (would be a force-push
     even without `--force`).
  3. Rejects push from `main` if the local working tree is dirty.

### CLAUDE.md guardrails section

Plain-text restatement of the policy so Claude understands *why*
it's being blocked and writes code accordingly, rather than treating
hook rejections as bugs to work around.

## Notification behavior

The user wants macOS desktop notifications **whenever Claude reports
a finding**. "Finding" = an experimental result, gate verdict,
aggregate statistic, or paper-relevant observation. NOT status
updates, progress reports, or operational chatter.

Mechanism: Claude issues `osascript -e 'display notification "..."
with title "..."'` as a Bash tool call. The `osascript -e display
notification:*` pattern is in the `allow` list so this runs without
prompting.

This is *behavioral* enforcement — Claude has to do it. The CLAUDE.md
guardrails section makes the requirement explicit so it survives
sessions.

## What's gitignored vs tracked under `.claude/`

| Path | Status | Why |
| --- | --- | --- |
| `.claude/settings.json` | **tracked** | Project policy. The whole point. |
| `.claude/hooks/*.sh` | **tracked** | Project policy. |
| `.claude/commands/` (when added) | **tracked** | Slash commands shared by project. |
| `.claude/settings.local.json` | gitignored | Per-user overrides; machine-specific paths. |
| `.claude/scheduled_tasks.lock` | gitignored | Runtime artifact. |
| `.claude/audit.log` | gitignored | Per-session log. |
| `.claude/file-history/`, `sessions/`, `projects/`, `cache/`, `backups/` | gitignored | Per-user runtime; can be huge. |

## How to start Claude Code with this policy active

After cloning (or once-per-machine):

```bash
cd ~/Desktop/claude-sudoku-experiments
bash scripts/setup_hooks.sh      # activates .githooks/ via core.hooksPath
```

Every session:

```bash
cd ~/Desktop/claude-sudoku-experiments
claude                            # default permission mode loads .claude/settings.json
```

To authorize a real `harness.run_plan` window in the current session:

```bash
export BUDGET_AUTHORIZED=1
# run the harness.run_plan command...
# when done:
unset BUDGET_AUTHORIZED
```

Or one-shot for a single window:

```bash
BUDGET_AUTHORIZED=1 .venv/bin/python -m harness.run_plan \
    --puzzle gen_7x7_s1_00 --window-budget 8 --max-turns 200
```

## Open follow-ups (deliberately deferred)

- **Per-day budget cap.** A hook could track cumulative subscription
  spend per UTC day in `.claude/budget_daily.json` and refuse runs
  past a threshold. Useful but adds complexity. Skipped for v1; the
  per-launch `ask` + env-var gate already requires explicit consent
  per window.
- **UserPromptSubmit hook injecting current Phase status.** Would
  prevent drift like "Claude forgot we'd already closed the gate".
  Skipped for v1 — memory + CLAUDE.md already handle this; add only
  if the issue recurs.
- **Network policy.** `curl`/`wget`/`ssh` currently fall to `ask`
  (per the user's choice). Tighten to `deny` if a future session
  shows Claude reaching for them unexpectedly.

## How to verify the policy is working

After starting Claude Code in a session:

```bash
# Try a blocked operation (should be rejected):
git push --force                  # settings deny
# Try a budget-gated operation (should ask):
.venv/bin/python -m harness.run_plan --puzzle gen_7x7_s1_00
# Tail the audit log to see Claude's actions:
tail -f .claude/audit.log
```

If `audit.log` is growing as Claude does things and the blocked
ops fail clean, the policy is live.
