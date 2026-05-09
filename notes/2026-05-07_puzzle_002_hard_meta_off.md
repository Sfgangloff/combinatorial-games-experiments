# puzzle_002 hard matrix (meta-off only) — 2026-05-07

## Setup

Single puzzle (`puzzle_002`), 7×7 Hard from puzzle-loop.com (task string
`322a2e23a331a3f3b2a13a2b3a213a2d222`, Puzzle ID 25,425). 23 numbered cells,
112 edges total.

Verified before running:
- Parses cleanly with `core.parser.load_from_text`.
- **Tier 3** by our own engine: a propagate-then-1-ply-lookahead loop
  (mirroring `slitherlink-coarse`'s `suggest_next_move`) plateaus at step 17
  with 68 of 112 edges still unknown. The coarse engine alone cannot finish.
- Backtracking solver confirms a unique solution in 0.35s.

Only the four meta-off cells were run — the meta axis was inert on
puzzle_001 (see companion note). Across two 5-hour rate-limit windows:

- Window 1 (~02:00 KST): full 8-cell matrix attempted. `none_meta-off`
  consumed ~$5.28 / 30 min and `none_meta-on` partially ran for ~$1.63 before
  the 5h cap rejected the remaining 6 cells (each aborted in ~3s with 0 calls).
- Window 2 (~17:21 KST, immediately after reset): the three remaining
  meta-off cells (`fine`, `medium`, `coarse`) ran sequentially via
  `harness.run_subset` and all solved.

Model: `claude-opus-4-7[1m]`. `max_turns=200`. n=1 per cell.

## Results

| toolset | meta | solved | calls | time     | cost    | ratio vs coarse |
|---------|------|--------|------:|---------:|--------:|----------------:|
| none    | off  | Y      |   2   | 1776.2s  | $5.28   | 2.28×           |
| fine    | off  | Y      | 124   | 1287.6s  | $4.99   | 2.15×           |
| medium  | off  | Y      |  51   |  830.6s  | $3.61   | 1.56×           |
| coarse  | off  | Y      |  51   |  613.3s  | $2.32   | 1.00× (baseline)|

Total spent on puzzle_002 meta-off cells: **$16.20**. Sequential wall time
~75 min (window 1's `none_meta-off` was sequential to window 2's three).

## Observations

- **All four toolsets solved a Tier 3 puzzle**, including `coarse` despite
  the engine-only test predicting it would plateau at step 17 with
  68/112 edges still unknown. The model successfully picked up where
  `suggest_next_move` returned `{"method": "stuck"}`, made its own
  placements, and the engine resumed propagating once new edges fed it
  fresh constraints. The "engine ceiling" is **soft** — the model can step
  around it.

- **Cost ratios across toolsets are surprisingly stable across difficulty.**
  Comparing puzzle_001 (5×5 easy) vs puzzle_002 (7×7 hard):

  | toolset | puzzle_001 ratio | puzzle_002 ratio |
  |---------|-----------------:|-----------------:|
  | none    | 2.30×            | 2.28×            |
  | fine    | 2.59×            | 2.15×            |
  | medium  | 1.86×            | 1.56×            |
  | coarse  | 1.00×            | 1.00×            |

  Coarse maintains its ~2× advantage over none/fine on both. The earlier
  prediction that the gap would *widen* with difficulty (recorded in
  `memory/none_toolset_scales_steeply.md`) was wrong — it stays roughly
  invariant. The "winner" doesn't change as you scale up; it just becomes
  more expensive in absolute terms.

- **`none` flipped from cheap to most-expensive.** On puzzle_001, `none`
  ($1.29) was *cheaper* than `fine` ($1.45). On puzzle_002, `none` ($5.28)
  is *more expensive* than `fine` ($4.99). The model's inline reasoning
  chain on a hard puzzle outweighs the tool-use overhead of placing every
  edge by hand. Pure reasoning is no longer the cheap baseline at this
  difficulty.

- **`fine`'s call count tracks edge count almost linearly.** 65 calls on
  puzzle_001 (60 edges) → 124 calls on puzzle_002 (112 edges). The pattern
  is "place every edge individually", scaled to the larger board.

- **`medium` and `coarse` had identical call counts (51 each).** The
  difference between the two is in the *quality* of each engine response
  (medium has only `forced_moves`, coarse has `forced_moves` + 1-ply
  lookahead in `suggest_next_move`), not in the number of model-engine
  round-trips. The cost gap ($3.61 vs $2.32) is therefore in output
  tokens — `medium`'s model writes more reasoning between calls because
  it doesn't get lookahead suggestions for free.

- **Time scaling is not uniform.**
  - none: 358.9s → 1776.2s (5.0×)
  - fine: 280.9s → 1287.6s (4.6×)
  - medium: 276.5s → 830.6s (3.0×)
  - coarse: 150.9s → 613.3s (4.1×)
  
  `medium`'s 3.0× is the gentlest scaling — possibly because `forced_moves`
  is doing more useful work per call as the engine has more constraints
  to chew on.

- **Rate-limit operational lesson confirmed.** A full 8-cell matrix on a
  hard puzzle does not fit in a single 5h window: just `none_meta-off` +
  partial `none_meta-on` consumed enough budget to reject the other 6.
  Future hard-puzzle runs should bucket cells by expected cost and stay
  under ~$8-10 per window.

## Caveats / next steps

- n=1 per cell. Differences could be variance.
- One puzzle per difficulty tier. We have a 5×5 easy and a 7×7 hard.
  Need ≥3 puzzles per tier and ≥2 tiers in between to claim "ratios
  stable across difficulty" robustly.
- Single model (Opus 4.7). Granularity preference may depend on model
  capability — stronger models may prefer finer-grained tools (more
  control), weaker ones coarser (more delegation). Worth testing with
  Sonnet/Haiku.
- **Training contamination risk:** puzzle-loop.com puzzles are public; the
  model may have seen this specific task string during training. The
  near-identical cell counts (medium/coarse both 51) hint at deterministic
  rather than reasoned behaviour. A held-out set or freshly generated
  puzzles would address this.
- We never observed the failure mode where the model gets *stuck* with no
  toolset able to make progress. Need a Tier 4+ puzzle (or larger grid)
  to find the model's ceiling, not just the engine's.
