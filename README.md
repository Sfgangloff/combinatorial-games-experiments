# Slitherlink MCP-tool granularity experiments

A research codebase comparing **tool granularities** for an LLM
(Claude Code) solving Slitherlink puzzles. The hypothesis is that
*how* a tool exposes work — many fine primitives vs. a handful of
named deductions vs. one coarse "suggest a move" — materially affects
an agent's cost-to-solve and solve-rate. The directory name
`claude-sudoku-experiments` is historical (Sudoku may return later).

Slitherlink rules: `rules.md`. Project context for Claude Code:
`CLAUDE.md`. Research plan, dated experiment notes, and lit review
live under `notes/`.

## Tool granularities under comparison

Five MCP servers under `servers/`, each exposed to the model by the
harness one condition at a time. The point isn't to hand Claude a SAT
solver — it's to vary *where* the model/engine boundary sits and
measure the effect.

| Set         | Tools                                              | Philosophy |
| ---         | ---                                                | --- |
| none        | judge tools only (`get_puzzle`, `submit_solution`) | Pure-reasoning baseline. |
| fine        | ~15 atomic primitives (`get_edge`, `set_edge`, `count_edges_at_dot`, …) | Tools track state; model does all inference. |
| medium      | ~9 named deductions (`apply_edge` w/ propagation, `forced_moves`, `endpoints`, …) | Tools handle one-step local inference. |
| coarse      | ~5 tools incl. `suggest_next_move` (propagate + 1-ply lookahead) | Tool does most of the work; control condition. |
| scratchpad  | medium + frame stack (`assume`/`commit`/`retract`) + `try_both` | Auto-bookkeeping for case-splits + engine-level 1-ply lookahead. |

Metrics: solve success, tool-call count, cost (USD), tokens,
dead-ends/backtracks, wall time.

## Layout

```
README.md, CLAUDE.md, rules.md         project context
core/                                  shared engine
  state.py, parser.py, render.py
  propagation.py, analysis.py
  generator.py                         seeded procedural generator
                                       + solution counter (uniqueness
                                       verifier) + difficulty tiering
servers/
  slitherlink-judge/                   get_puzzle, submit_solution
  slitherlink-fine/                    ~15 atomic primitives
  slitherlink-medium/                  ~9 local-deduction tools
  slitherlink-coarse/                  suggest_next_move + apply_move
  slitherlink-scratchpad/              medium + frame stack + try_both
harness/
  run.py            run one (puzzle x condition) cell
  run_subset.py     run a subset of toolsets on one puzzle
  run_matrix.py     run the full N-condition matrix
  run_plan.py       resumable, window-budget-capped, rate-limit-safe
                    batch runner; --dry-run shows pending trials
  conditions.py, prompts.py, aggregate_phase1.py, visualize.py
tests/                                 smoke tests for core/ and servers
puzzles/                               test corpus + manifest.json
notes/                                 dated experiment notes + lit review
legacy/                                prior file-based batch protocol
                                       (read-only reference)
```

## Running

```
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
python -m tests.run_all                # smoke tests
python -m core.generator --selftest    # generator + uniqueness verifier
```

Register a server with Claude Code:

```
claude mcp add slitherlink-scratchpad -- \
    /absolute/path/to/.venv/bin/python \
    /absolute/path/to/servers/slitherlink-scratchpad/server.py
```

Drive experiments via the resumable runner (see `harness/run_plan.py`
for the budget/resume semantics — designed for the 5h-rate-limit
regime, idempotent across windows):

```
python -m harness.run_plan --dry-run                        # show pending plan
python -m harness.run_plan --window-budget 8 --max-turns 200
```

The runner scans `harness/results/`, counts already-good trials per
cell, and resumes by running only what's missing. It aborts cleanly
on any fatal SDK/rate-limit error so a closed window doesn't burn the
remaining plan.

## `legacy/` — what's archived there

`legacy/slitherlink-batch-experiment/` contains an earlier attempt
using a strict file-based **batch protocol** (5 elementary moves per
batch, file-based reasoning traces, a verifier script). It taught us
that contract-enforcement scripts catch protocol violations but don't
help the model reason better, and that bookkeeping overhead crowded
out actual deduction — motivating the move to MCP tools. Preserved
verbatim:

- `reasoning_step_1.txt` … `reasoning_step_12.txt` — example outputs
- `verify_batch.py` — the contract verifier
- `slitherlink_strategy.md`, `specific_solving_guide.md`,
  `solving_guide.md` — heuristics
- `failure_playbook.md`, `chatgpt_improvement_plan.md`, `TODO.txt`
- `claude.md` — the original project instructions
- `grid_step_0.txt` — the 5×5 puzzle used

These are kept verbatim for reference. Don't modify them.
