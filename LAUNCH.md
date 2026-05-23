# How to launch Claude Code on this project

A short cheat-sheet so you don't have to remember the dance. Full
rationale: `notes/2026-05-22_guardrails_design.md`. Policy: `CLAUDE.md`
+ `.claude/settings.json`.

## First time on a machine (once per clone)

```bash
cd ~/Desktop/claude-sudoku-experiments
bash scripts/setup_hooks.sh
```

This activates the git hooks in `.githooks/` (sets `core.hooksPath`)
and makes the Claude hook scripts in `.claude/hooks/` executable.

## Every session — normal work (no compute spend)

```bash
cd ~/Desktop/claude-sudoku-experiments
claude
```

That's it. The `.claude/settings.json` checked into the repo loads
automatically. Permissions, hooks, deny-list — all active. Routine
Bash commands, git operations up to `git push origin`, file reads,
file edits inside the repo, and MCP tool calls run without prompts.

## When you want Claude to actually launch a harness window

The `harness.run_plan` (without `--dry-run`) is the only thing that
burns subscription compute, and it's the only routinely-needed
command that's gated. Two options:

### Option A — authorize for the whole session

```bash
cd ~/Desktop/claude-sudoku-experiments
export BUDGET_AUTHORIZED=1
claude
```

While `BUDGET_AUTHORIZED=1` is set in the shell where you launched
Claude, Claude can launch as many windows as you tell it to. `unset
BUDGET_AUTHORIZED` (or close the terminal) when done.

### Option B — authorize just one command

```bash
BUDGET_AUTHORIZED=1 claude
```

Same effect, scoped to that single Claude process.

### Always-free planning

```
.venv/bin/python -m harness.run_plan --dry-run
```

Always allowed. Shows what would run, without spending anything.

## What's blocked (so nothing surprises you)

- `git push --force` (any flavor), `git reset --hard`, `git checkout
  -- *`, `git clean -fd`, `git branch -D`
- `git commit --no-verify`, `git commit --amend`, `git rebase`
- `rm -rf`, `sudo`, `dd`, `mkfs`, `chown`, recursive `chmod -R`
- Edits to `legacy/`, `.git/internals`, `/etc/`, `~/.ssh/`
- Edits to anywhere outside the repo root
- `harness.run_plan` without `--dry-run` if `BUDGET_AUTHORIZED` is unset

If you ever need one of these for a genuine reason, run it directly
in your own shell (you have full access; only Claude is gated).

## Where to look if something feels off

```bash
tail -50 .claude/audit.log     # every Bash command Claude has run
git log --oneline -20          # commit history (Co-Authored-By marks Claude commits)
git status                     # working-tree state
```

## Files that define the policy

| File | What it does |
| --- | --- |
| `.claude/settings.json` | Permissions (allow/deny/ask) + hook registration. Tracked. |
| `.claude/settings.local.json` | Your per-machine overrides. **Gitignored.** |
| `.claude/hooks/*.sh` | Path check, bash audit, end-of-turn summary. Tracked. |
| `.githooks/pre-commit` | Rejects committing forbidden paths; runs generator selftest. Tracked. |
| `.githooks/pre-push` | Rejects deletion of main, non-ff push to main. Tracked. |
| `scripts/setup_hooks.sh` | One-shot activator after clone. Tracked. |
| `CLAUDE.md` | What Claude reads to understand the rules. Tracked. |

## When to change the policy

Edit `.claude/settings.json` (and re-commit) if:

- A routine command keeps prompting → add a more specific `allow`.
- Claude does something you wish it hadn't → add a `deny`.
- The budget gate is too aggressive / not aggressive enough → adjust
  `.claude/hooks/check_bash.sh`.

For machine-local tweaks that shouldn't be shared (paths to your
specific Python, etc.), use `.claude/settings.local.json` instead.
That file is gitignored and never leaves your machine.
