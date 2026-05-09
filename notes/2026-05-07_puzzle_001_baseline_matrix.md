# puzzle_001 baseline matrix — 2026-05-07
# (See companion: 2026-05-07_puzzle_002_hard_meta_off.md)

## Setup

Single puzzle (`puzzle_001`) run through the full 8-condition matrix from
`harness/run_matrix.py`:

- **toolset**: `none` / `fine` / `medium` / `coarse` — controls which
  slitherlink-solving MCP server (if any) is exposed to the model. `none` only
  has the judge tools (`get_puzzle`, `submit_solution`); the others add a
  slitherlink-{fine,medium,coarse} server with progressively higher-level
  primitives.
- **meta**: `off` / `on` — toggles the meta-tools MCP server
  (`analyze_trajectory`, `develop_tool`).

Model: `claude-opus-4-7[1m]`. `max_turns=35`. One run per cell — n=1.

The matrix had been attempted the previous evening (2026-05-06) but six of the
eight cells aborted in ~3s with a five-hour rate-limit rejection
(`overage_status='rejected'`, `overage_disabled_reason='org_level_disabled'`).
This run is the clean re-execution after the limit reset.

## Results

| toolset | meta | solved | tool calls | time    | cost  |
|---------|------|--------|-----------:|--------:|------:|
| none    | off  | Y      |  3         | 358.9s  | $1.29 |
| none    | on   | Y      |  3         | 236.5s  | $0.77 |
| fine    | off  | Y      | 65         | 280.9s  | $1.45 |
| fine    | on   | Y      | 67         | 286.9s  | $1.27 |
| medium  | off  | Y      | 22         | 276.5s  | $1.04 |
| medium  | on   | Y      | 22         | 425.3s  | $1.52 |
| coarse  | off  | Y      | 24         | 150.9s  | $0.56 |
| coarse  | on   | Y      | 24         | 250.7s  | $0.97 |

Total wall time: 38.1 min. Total cost: ~$8.87.

Raw per-run JSON lives in `harness/results/2026050[6-7]T*_puzzle_001_*.json`;
the run log is `harness/results/_matrix_run.log`.

## Observations

- **Every condition solved puzzle_001.** Toolset granularity did not determine
  *whether* the puzzle was solvable here — only the cost/calls profile.
  puzzle_001 is therefore too easy to discriminate between toolsets on the
  success axis; future runs need harder puzzles if we want solve-rate signal.

- **`coarse_meta-off` is the efficiency winner** at 150.9s / $0.56 / 24 calls
  — about 2.5× faster and less than half the cost of the next-cheapest cell.

- **`fine` uses ~3× the tool calls of `medium`/`coarse`** (65–67 vs. 22–24)
  for similar wall time and slightly higher cost. The atomic primitives appear
  to push the model into a per-edge interrogation pattern; the higher-level
  toolsets let it accomplish equivalent reasoning steps in fewer round-trips.

- **`none`** (pure reasoning + submit) is competitive at 3 calls — but those
  calls are doing a lot of hidden work and the total cost lands mid-pack
  ($0.77–$1.29). Submission is essentially "one shot reasoning, then submit".

- **The `meta` axis was effectively inert: no meta-tool was ever called.**
  `meta=on` exposed `analyze_trajectory` and `develop_tool` but the model
  invoked neither in any of the 4 meta-on runs. This fully explains the
  identical call counts between meta-on and meta-off within each toolset
  (3/3, 65/67, 22/22, 24/24); the cost/time deltas across that axis are
  pure variance. Meta-tools are gated by self-observation triggers
  ("I'm repeating a 3-step workaround") that don't fire when the model has
  task-appropriate tools at hand.

## What tools did each toolset actually use?

Each toolset induced a distinct solving pattern, driven by tool names alone
(no prompt instruction directed the model to use them):

- **fine** — brute placement: `set_edge` ×60 + `render` ×1–3 + `solved` ×1.
  Atomic primitive ⇒ model does inference in its head and just records the
  result, one edge at a time.
- **medium** — mixed: `apply_edge` ×11–14, `forced_moves` ×1–3, `render` ×3,
  `endpoints` ×0–1, `solved` ×1. The model uses the higher-level
  `forced_moves` inference helper but sparingly, and falls back to placement.
- **coarse** — driver loop: `suggest_next_move` ×8 + `apply_move` ×8 +
  `state` ×4 + `solved` ×1. The suggest tool advertises "I'll do the
  reasoning," and the model essentially becomes a thin driver consuming its
  output.
- **none** — `get_puzzle` (+ optional `list_puzzles`) + `submit_solution`.
  All reasoning is text-internal.

## Caveats / next steps

- n=1 per cell. No statistical claims possible — all the deltas above could be
  variance.
- Single puzzle, and an easy one (everything solved). Need a puzzle set with
  variable difficulty to see where toolsets start to differentiate.
- Did not inspect the per-run trajectories to confirm *which* tools were used
  (especially whether meta-tools fired at all under `meta=on`). Worth checking
  before drawing conclusions about meta.
- Five-hour rate limit is a real budgeting constraint: this 8-cell run cost
  ~$8.87 and ~38 min of wall time. A 4-puzzle × 8-cell sweep would likely
  exceed the limit.
