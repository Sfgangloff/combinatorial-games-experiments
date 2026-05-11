# slitherlink-scratchpad sweep — 4 puzzles, increasing difficulty

**Date:** 2026-05-10. **Status:** complete. 5h rate-limit hit during
puzzle_004 (resets 17:40 KST), so puzzle_003 errored immediately.
**Setup:** scratchpad toolset only, meta-off, max-turns=200, n=1 per
puzzle. Sequential via `harness.run_subset`, chained with `&&` so a
rate-limit hit cleanly stops the remaining runs.

This is the first end-to-end test of the scratchpad design
(`notes/2026-05-09_scratchpad_toolset_design.md`). Goals:

1. Sanity-check on puzzle_001 (5×5 easy).
2. Compare to medium on puzzle_002 (7×7 hard) — does scratchpad
   match or beat medium?
3. Real test on puzzle_004 (15×15 hard) — does it solve where all 4
   prior toolsets failed?
4. Bail-or-engage on puzzle_003 (25×30 hard).

## Results so far

| puzzle | size  | difficulty | solved | calls | time      | cost   | submit attempts |
|--------|------|------------|:------:|------:|----------:|-------:|---------------:|
| 001    | 5×5   | easy       | **Y**  |    25 |   6.0 min |  $1.50 | 1              |
| 002    | 7×7   | hard       | **Y**  |    37 |  10.9 min |  $2.58 | 1              |
| 004    | 15×15 | hard       | N (rate-limited) | 165 | 53.1 min | $21.17 | 0 |
| 003    | 25×30 | hard       | N (degenerate)   |   0 |   3.4 s  |  $0.00 | 0 |

## Comparison vs prior runs

### puzzle_001 (5×5 easy) — Phase-1 had n=3-4 per cell

| toolset (meta-off) | n | cost μ ± σ      | solved (rate) |
|--------------------|---|-----------------|---------------|
| coarse             | 3 | $0.82 ± $0.31   | 100%          |
| none               | 4 | $1.15 ± $0.14   | 100%          |
| medium             | 4 | $1.18 ± $0.20   | 100%          |
| **scratchpad**     | 1 | **$1.50**       | **100%**      |
| fine               | 3 | $1.71 ± $0.50   | 100%          |

Scratchpad falls between medium and fine. Within Phase-1's variance
band (fine ± 1σ overlaps scratchpad's $1.50). Sanity ✓.

### puzzle_002 (7×7 hard) — May 7 baseline n=1 per cell

| toolset (meta-off) | solved | calls | time     | cost   |
|--------------------|:------:|------:|---------:|-------:|
| coarse             | Y      |  51   |  10.2 min| $2.32  |
| **scratchpad**     | **Y**  |  **37** | **10.9 min**| **$2.58** |
| medium             | Y      |  51   |  13.8 min| $3.61  |
| fine               | Y      | 124   |  21.5 min| $4.99  |
| none               | Y      |   2   |  29.6 min| $5.28  |

**Scratchpad is essentially tied with coarse** ($2.58 vs $2.32, an
11% gap that's well within the Phase-1 σ for any condition) and
**~28% cheaper than medium** ($2.58 vs $3.61). Fewer calls than
medium/coarse (37 vs 51) suggest the model is doing more reasoning
between calls but converging faster.

### Puzzle_002 tool-call breakdown for scratchpad

```
apply_edge       18
render            9
endpoints         4
forced_moves      2
get_puzzle        1
load              1
solved            1
submit_solution   1
```

**Zero frame primitives used.** No `assume`, no `commit`, no
`retract`, no `frames`, no `current_frame`. The model solved 7×7
hard purely with the medium-tier deduction tools — frames sat
unused.

### Puzzle_001 tool-call breakdown

```
apply_edge       12
render            7
get_puzzle        1
load              1
forced_moves      1
assume            1   ← used once, but no matching commit/retract
solved            1
submit_solution   1
```

The model called `assume` once on puzzle_001 but never followed up
with `commit` or `retract`. The frame was left dangling; the model
submitted via the judge anyway (judge takes a grid string, not a
handle, so the dangling frame is harmless). Possibly the model used
the assume to "test" a hypothesis, decided what it learned was
enough, and moved on — without realising that committing would
preserve the deductions for downstream calls.

## Observations so far

1. **Sanity ✓**: scratchpad solves easy and 7×7 hard cleanly.
2. **Beats medium on 7×7 hard** ($2.58 vs $3.61, 28% cheaper). Ties
   coarse. So at minimum, the snapshot/restore overhead in medium
   was real and removing it helped.
3. **Frames are not yet doing work.** On puzzle_002 the model solved
   without ever calling `assume`. This means scratchpad's puzzle_002
   win is *not* attributable to frame-based bookkeeping — it's
   "medium minus snapshot/restore noise". The frames hypothesis is
   not yet tested.
4. **Puzzle_004 (15×15 hard) is now the real test.** If the model
   uses frames substantially there and solves (or at least submits a
   valid partial), the frame hypothesis is validated. If it doesn't
   use frames *or* doesn't solve, the design needs revisiting:
   maybe the system prompt should explicitly invite the model to
   use `assume` on hard puzzles, or maybe frames are unnecessary
   and we should stop and reframe.
5. **Possible model-side issue**: the model may not know *when* to
   reach for frames. The prompt doesn't currently mention them. On
   easy puzzles greedy propagation is enough; on 7×7 it was still
   enough; on 15×15 it shouldn't be — and the puzzle_004 result
   will tell us if the model finds frames or just gives up the way
   medium did.

## puzzle_004 (15×15 hard) — the real test

### Comparison vs prior 4-toolset run (all n=1)

| toolset (meta-off) | solved | calls | time     | cost     | submit attempts |
|--------------------|:------:|------:|---------:|---------:|----------------:|
| none               | N      |    1  |   36 s   |  $0.10   | 0               |
| coarse             | N      |   99  |   13 min |  $3.21   | 0               |
| fine               | N      |  126  |   19 min |  $4.25   | 0               |
| **scratchpad**     | **N (rate-limited)** | **165** | **53 min** | **$21.17** | **0** |
| medium             | N      |  162  |   63 min |  $29.93  | 0               |

**Scratchpad is 29% cheaper than medium at the same (failed) outcome.**
Both stopped without submitting. Scratchpad ran the model into the
5h rate limit; medium gave up voluntarily.

### Tool-call breakdown for puzzle_004 scratchpad

```
apply_edge          77
render              23
endpoints           21
assume              11   ← used substantively at 15×15
retract             11   ← matches assume; all hypotheses retracted
forced_moves         9
check_consistency    8
frames               2
load                 2
get_puzzle           1
commit               0   ← never committed; zero forward progress from frames
current_frame        0
```

**The model used frames on its own** without the prompt mentioning
them. 11 `assume`s, 11 `retract`s, 0 `commit`s — flat (no nesting)
case-splits, every one of which the model abandoned. Depth cap of 5
never came into play.

## Read on the frame hypothesis

The design predicted that auto-bookkeeping would let the model solve
harder puzzles at lower cost. Half-validated:

**Supports the hypothesis:**

- The model finds frames at 15×15 without being told. So the
  primitive is discoverable — the design isn't dead from
  unfamiliarity.
- 29% cost reduction at the same task (failed solve) vs medium.
  Auto-bookkeeping is real and cheap.
- Retract/assume counts match (11/11), no dangling frames. The
  engine semantics work as designed.

**Does not support the hypothesis:**

- Didn't actually solve. Same failure mode as medium — case-split
  rabbit hole.
- **Zero `commit`s.** Every hypothesis was retracted. The model
  never accumulated forward progress from a frame.
- This suggests the model is *failing every assumption*. Either it's
  picking bad splits (no edge has a unique forced answer), or each
  split contradicts because the puzzle requires deeper than 1-edge
  hypothesis to bear fruit.
- The negation-on-retract feature was technically active but didn't
  appear to break the cycle.

## puzzle_003 (25×30) — degenerate, no data

0 tool calls in 3.4s with rate-limit error. The 5h cap from puzzle_004
was still active when the next process launched. Treat as "no data
collected" rather than "scratchpad failed on 25×30."

## Bottom line

The scratchpad design works mechanically and gives a real cost
saving at the failure boundary (29% under medium at 15×15 hard), but
the *frames-only* hypothesis is **not enough to break the 15×15
ceiling**. Reducing bookkeeping cost was necessary but not
sufficient; the model still doesn't know what to assume.

The original design proposal listed `try_both` as a v2 candidate
that was held back for clean attribution. The puzzle_004 trace —
11 assumes, 0 commits — is exactly the failure mode `try_both`
would address: instead of the model picking one branch to test, the
engine tries both branches of a single edge and reports which (if
any) survives. That converts "11 failed hypotheses" into "11
forced edges (when only one branch survives)."

## Followups

- **v2 with `try_both`** as a single tool: scratchpad-current minus
  the model's role in picking branches. If puzzle_004 solves with
  v2, the puzzle was always one-ply-deep deductions away from
  finishing — the bottleneck was the model's branch selection, not
  the search itself.
- **Inspect puzzle_004 messages** to see *which* edges the model
  assumed and whether any was a near-miss (would have led to
  progress with one more apply_edge or a different value).
- **Replicate** puzzle_002 + puzzle_004 with n≥3 before quoting
  these costs as stable. The cost gap of $21 vs $30 could
  partially be variance.
- **Re-run puzzle_003** after the rate-limit window resets, to
  get a real data point.
