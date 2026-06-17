# Slitherlink MCP tool-granularity experiments

Experiment code for a study of how **MCP tool-set granularity** affects an
LLM agent (Claude Code, Opus 4.7) solving Slitherlink puzzles — fine atomic
primitives vs. named one-step deductions vs. a coarse "suggest a move" tool,
plus a `scratchpad` variant with engine-level bookkeeping and 1-ply lookahead.

> **The research reasoning lives elsewhere.** Questions, answers, conclusions,
> and how the project's thinking evolved are maintained as a structured
> reasoning graph in the **research-compiler** repo, stream
> **`slitherlink-tool-granularity`**. This repository keeps only the
> experiment apparatus + data. To read the reasoning:
> `rc export paper --stream slitherlink-tool-granularity` (or open it in the
> research-compiler web app). Each experiment below is the node `e-00NN` in
> that stream.

## Tool granularities under comparison

Five MCP servers under `servers/`, exposed to the model one condition at a time.

| Set         | Tools                                              | Philosophy |
| ---         | ---                                                | --- |
| none        | judge tools only (`get_puzzle`, `submit_solution`) | Pure-reasoning baseline. |
| fine        | ~15 atomic primitives (`get_edge`, `set_edge`, …)  | Tools track state; model does all inference. |
| medium      | ~9 named deductions (`apply_edge`, `forced_moves`, …) | Tools handle one-step local inference. |
| coarse      | ~5 tools incl. `suggest_next_move` (propagate + 1-ply) | Tool does most of the work; control condition. |
| scratchpad  | medium + frame stack (`assume`/`commit`/`retract`) + `try_both` | Auto-bookkeeping for case-splits + engine 1-ply lookahead. |

Metrics: solve success, tool-call count, cost (USD), tokens, backtracks, wall time.

## Experiment index

Each row is a node in the `slitherlink-tool-granularity` stream. The harness
writes raw per-trial JSON to `harness/results/` (gitignored).

| Node | Experiment | How to run |
| --- | --- | --- |
| `e-0001` | puzzle_001 (5×5 easy) 2×4 baseline matrix (pilot) | `python -m harness.run_matrix` |
| `e-0002` | puzzle_002 (7×7 hard) 4-toolset pilot | `python -m harness.run_subset` |
| `e-0003` | puzzle_001 Phase-1 replication, n=3–4 | `python -m harness.run_subset` → `python -m harness.aggregate_phase1` |
| `e-0004` | puzzle_002 Phase-1 gate replication, n=3 | `python -m harness.run_plan` |
| `e-0005` | puzzle_004 (15×15) scaling probe | `python -m harness.run_subset` |
| `e-0006` | scratchpad v1 (frame stack) sweep | `python -m harness.run_subset` (server `slitherlink-scratchpad`) |
| `e-0007` | scratchpad v2 (`try_both`, 1-ply) sweep | `python -m harness.run_subset` |
| `e-0008` | puzzle_004 scratchpad meta-on probes | `python -m harness.run_plan` |
| `e-0009` | gen_7x7_s1_00 Phase-2 frontier, n=3 | `python -m harness.run_plan` → `python -m harness.analyze_phase2` |
| `e-0010` | model × granularity sweep (Haiku/Sonnet/Opus × 7×7 ladder), n≥3 — *planned* | `python -m harness.run_model_grid` → `python -m harness.analyze_model_x_granularity` (see `notes/2026-06-09_model_x_granularity.md`) |
| `e-0011` | reasoning-externalization decomposition (turns × $/turn) on existing trials — *no new compute* | `python -m harness.analyze_efficiency_frontier` (see `notes/2026-06-10_reasoning_externalization.md`) |
| `e-0012` | context-tax decomposition: output-token saving minus cache-read tax reproduces the Goldilocks cost gap (corr 0.998) on existing trials — *no new compute* | `python -m harness.analyze_context_tax` |

Difficulty is a *computed* property: `core.generator.grade` tiers each puzzle
(1 = propagation, 2 = +1-ply, 3+ = search, with `search_nodes`). Frontier
puzzles are procedurally generated with seed-locked uniqueness verification
(`python -m core.generator --selftest`).

## Layout

```
core/        shared engine (state, parser, render, propagation, analysis, generator)
servers/     the five MCP toolsets (judge / fine / medium / coarse / scratchpad)
harness/     run.py, run_subset.py, run_matrix.py, run_plan.py (resumable,
             budget-capped, rate-limit-safe), run_model_grid.py (model ×
             granularity, model-aware resume + own budget gate),
             conditions.py, prompts.py, aggregate_phase1.py,
             analyze_phase2.py, analyze_model_x_granularity.py,
             analyze_efficiency_frontier.py, visualize.py
puzzles/     test corpus + manifest.json + generated frontier puzzles
tests/       smoke tests for core/ and servers/
legacy/      prior file-based batch protocol — FROZEN reference, do not edit
rules.md, validate_grid.py, pyproject.toml
```

## Running

```
python3 -m venv .venv && source .venv/bin/activate && pip install -e .
python -m tests.run_all                # smoke tests
python -m core.generator --selftest    # generator + uniqueness verifier

# Register a server with Claude Code, e.g.:
claude mcp add slitherlink-scratchpad -- \
    /absolute/path/to/.venv/bin/python \
    /absolute/path/to/servers/slitherlink-scratchpad/server.py

# Drive experiments via the resumable runner:
python -m harness.run_plan --dry-run                  # show pending plan (free)
python -m harness.run_plan --window-budget 8 --max-turns 200
```

`harness/run_plan` is designed for the 5h-rate-limit regime: it scans
`harness/results/`, counts good trials per cell, and resumes only what's
missing, aborting cleanly on any fatal SDK/rate-limit error.

## `legacy/` — archived reference

`legacy/slitherlink-batch-experiment/` is an earlier file-based **batch
protocol** attempt (5 moves/batch, file-based reasoning traces, a verifier).
It taught us that contract-enforcement scripts catch protocol violations but
don't help the model reason, and that bookkeeping overhead crowds out
deduction — motivating the move to MCP tools. **Frozen; do not modify.**
