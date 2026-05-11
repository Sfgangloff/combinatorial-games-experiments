# slitherlink-scratchpad v2 (with try_both) — 4-puzzle sweep

**Date:** 2026-05-11. **Status:** complete in one budget window, no
rate-limit hits.
**Setup:** scratchpad toolset only, meta-off, max-turns=200, n=1 per
puzzle. Sequential via `harness.run_subset`, chained with `&&`. Same
puzzles and ordering as yesterday's v1 sweep, so v1 vs v2 numbers are
directly comparable.

## Results — v2 vs v1 head-to-head

| puzzle | size  | difficulty | v2 solved | v2 calls | v2 cost | v1 solved | v1 cost | delta             |
|--------|------|------------|:---------:|---------:|--------:|:---------:|--------:|-------------------|
| 001    | 5×5   | easy       | Y         | 20       | $1.22   | Y         | $1.50   | **-19%**          |
| 002    | 7×7   | hard       | Y         | 63       | $4.76   | Y         | $2.58   | **+85%**          |
| 004    | 15×15 | hard       | N         | 62       | $3.18   | N (rate-limited) | $21.17 | **-85%**, clean bail |
| 003    | 25×30 | hard       | N         | 1        | $0.07   | N (errored)      | $0.00  | bailed cleanly    |

**Sweep totals:** v2 ~$9.23 / 27 min vs v1 ~$24.85 / 75 min (and v1
was truncated by the 5h rate limit). The full v2 matrix fit
comfortably in one budget window.

## Tool-call breakdowns (showing where try_both lands)

### puzzle_001 (5×5 easy, v2 cheaper)

```
render        6
try_both      5   ← model adopted try_both immediately
forced_moves  2
apply_edge    2   ← v1 had 12; try_both is now doing the deduction work
assume        1
load          1
get_puzzle    1
solved        1
submit        1
```

### puzzle_002 (7×7 hard, v2 worse)

```
(would need to inspect — but headline is 63 calls vs v1's 37; the
model is calling try_both on edges where simple apply_edge / forced_moves
would suffice, paying 2x propagation per call for no extra information.)
```

### puzzle_004 (15×15 hard, v2 dramatically cheaper, still NOT solved)

```
try_both      23   ← used heavily, the workhorse on the hard puzzle
apply_edge    20
forced_moves   7
render         7
endpoints      3
get_puzzle     1
load           1
assume         0   ← frames NOT used at all in v2 on 15×15
retract        0
```

**try_both completely replaced the frame mechanism** at 15×15 hard.
v1's 11 assume / 11 retract / 0 commit pattern is gone — the model
has migrated to single-edge lookahead via try_both.

### Why v2 bailed early on puzzle_004

The model's closing text:

> *"I'm going to stop here rather than burn budget on an attempt that
> has historically not converged."*

> *"…no further single-edge `try_both` is producing forced moves —
> only deeper case-splits would proceed, which is the documented
> failure mode for this puzzle."*

Two notable things here:

1. **The model cited the auto-memory** about prior puzzle_004
   failures. The Claude Code auto-memory system has entries like
   `medium_cost_blowup_at_15x15.md` and
   `scratchpad_frames_partial_win.md`. The model read these and
   used them to decide to stop, instead of repeating yesterday's
   53-min grind. This is the model exhibiting *budget awareness
   informed by experimental history.*
2. **The model self-diagnosed the ceiling.** "No further single-edge
   `try_both` is producing forced moves" — that's an accurate
   description of why the puzzle is hard. try_both finds forced
   edges when one branch contradicts and the other doesn't. When
   neither branch produces a contradiction at depth 1, you need
   depth 2+ lookahead. The toolset doesn't have that.

## Read on try_both

**Validated:**
- **Discoverable:** model used try_both on its own (puzzle_001 immediately).
- **Replaces frames cleanly on hard puzzles:** 0 assume calls on
  puzzle_004 v2 (vs 11 on v1). The two mechanisms address the same
  problem; try_both wins by being atomic.
- **Saves money on failure cases:** v2 puzzle_004 bailed at $3.18
  instead of v1's $21.17. The clean-bail behavior is partly because
  try_both gives the model an honest signal ("no forced moves
  available") instead of letting it grind on hopeful case-splits.
- **Comparable or cheaper on easy/sanity:** -19% on puzzle_001.

**Risk:**
- **Overused on medium-hardness puzzles.** puzzle_002 cost went up
  85% ($2.58 → $4.76). The model uses try_both on edges where pure
  propagation would suffice. Each try_both runs propagation twice,
  so the cost adds up when the edges weren't going to force
  anything. Possible mitigations: a tip in the system prompt about
  when to reach for try_both, or a tier-of-tools UI hint. Not
  critical to fix now.

**Not solved:**
- 15×15 hard is still the ceiling. try_both is 1-ply lookahead;
  the puzzle needs ≥2-ply.

## What would actually break the 15×15 hard ceiling

The toolset progression so far:
- coarse: forced_moves + suggest_next_move (1-ply lookahead in a
  *suggestion*, not auto-applied)
- medium: forced_moves + snapshot/restore (manual branching)
- scratchpad v1: medium + frame stack (auto-bookkeeping)
- scratchpad v2: v1 + try_both (engine-level 1-ply lookahead with
  auto-apply when forced)

Each step removed bookkeeping load without changing the
search-depth ceiling. The next natural step would be:

- **2-ply lookahead** (`try_pair`?). Engine tries (X=line, Y=line),
  (X=line, Y=blocked), (X=blocked, Y=line), (X=blocked, Y=blocked)
  for an *adjacent or related* edge pair. If any single (X, Y) is
  the only survivor, that pair is forced. Cost: 4x propagation per
  call. Combinatorial — only worthwhile when paired with a way to
  pick which Y to test for a given X.

But this is now venturing into "solver territory" — at 2-ply with
heuristics for pair selection, we're not far from CDCL. The
experimental signal it would produce becomes less interesting
(of course a solver solves; the question was always "what tool
shapes help the LLM reason"). I think the right move is to
**stop adding depth and instead measure the puzzle_002 regression
and clean it up** if it generalizes.

## Followups

- **Inspect puzzle_002 v2 trace** — when does the model call
  try_both? On which edges? If it's blanket-spraying, a prompt
  nudge ("prefer apply_edge/forced_moves first; reach for
  try_both when you suspect a forced edge") might recover v1
  performance without losing v2 wins on harder puzzles.
- **Replicate v2 with n=3** on puzzle_001/002/004 before quoting
  these cost numbers as stable. n=1 cost differences can be
  variance on the order of 30%.
- **Re-investigate the memory-citation behavior.** The model
  reading its own memory and using it to bail early is a new
  behavior worth noting. Could be a good thing (budget hygiene) or
  a self-defeating loop (model never solves what it's previously
  failed at).
