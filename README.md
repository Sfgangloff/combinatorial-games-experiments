# claude-sudoku-experiments

Experiments on helping an LLM (Claude Code) solve logic puzzles. Currently focused on **Slitherlink**. Sudoku may return later.

## What's here now

The current goal is to build **MCP (Model Context Protocol) tool sets** that Claude can call while solving Slitherlink puzzles, and to compare different *granularities* of tooling — does the model do better with many small primitives, a medium-sized set of named deductions, or one coarse "suggest a move" tool?

We deliberately avoid handing Claude a SAT solver. The point isn't to solve the puzzle for it; it's to remove bookkeeping work (counting edges around dots, propagating one local rule, checking consistency) so the model can spend its capacity on actual reasoning.

### Layout

```
README.md                 - this file
CLAUDE.md                 - project context shown to Claude Code
rules.md                  - the rules of Slitherlink
validate_grid.py          - legacy validator script (kept for reference)
pyproject.toml            - package + deps (fastmcp)
core/                     - shared engine: state, parser, render, propagation, analysis
servers/
  slitherlink-fine/       - ~15 primitive tools, no inference (planned)
  slitherlink-medium/     - ~9 tools with local deductions baked in
  slitherlink-coarse/     - minimal tools + "suggest next move" (planned)
tests/                    - smoke tests for core/ and each server
puzzles/                  - test corpus (planned)
legacy/                   - prior experiments (see below)
```

### Running the servers

```
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
python -m tests.test_core            # core smoke test
python -m tests.test_medium_server   # medium server smoke test
```

To register a server with Claude Code:

```
claude mcp add slitherlink-medium -- \
    /absolute/path/to/.venv/bin/python \
    /absolute/path/to/servers/slitherlink-medium/server.py
```

### Tool granularities under comparison

| Set | Tools | Philosophy |
| --- | --- | --- |
| fine | ~15 primitives (`get_edge`, `set_edge`, `count_edges_at_dot`, …) | Tools track state; model does all reasoning. |
| medium | ~8 named deductions (`apply_edge` w/ propagation, `forced_moves`, `pattern_scan`, …) | Tools handle one-step local inference. |
| coarse | ~5 (`suggest_next_move` returns a move + narrative) | Tool does most of the work; control condition. |

Comparison metrics: solve success, tool-call count, tokens, dead-ends/backtracks, wall time.

## `legacy/` — what's archived there

`legacy/slitherlink-batch-experiment/` contains a previous attempt that took a very different approach: a strict file-based **batch protocol**. Claude was instructed (via `CLAUDE.md`) to perform exactly 5 elementary moves per "batch", write a `reasoning_step_N.txt` recording each step + the full grid state, and run a verifier script that enforced all the contract rules. The idea was to keep the human in the loop by forcing legible, inspectable, step-by-step work.

It taught us a few things — mainly that contract-enforcement scripts catch protocol violations but don't help the model reason better, and that the bookkeeping overhead (re-rendering the grid, counting edges by hand) was crowding out actual deduction. That motivated the move to MCP tools.

Files preserved:
- `reasoning_step_1.txt` … `reasoning_step_12.txt` — example batch outputs
- `verify_batch.py` — the contract verifier
- `slitherlink_strategy.md`, `specific_solving_guide.md`, `solving_guide.md` — heuristics and lessons learned (still useful as input for tool design)
- `failure_playbook.md`, `chatgpt_improvement_plan.md`, `TODO.txt` — meta-notes
- `claude.md` — the original project instructions for the batch protocol
- `grid_step_0.txt` — the 5×5 puzzle used in the experiment

These are kept verbatim for reference. Don't modify them.
