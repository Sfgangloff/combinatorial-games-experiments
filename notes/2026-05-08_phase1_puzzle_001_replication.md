# Phase 1 — puzzle_001 replication (n=3–4 per cell, meta-off)

**Date:** 2026-05-08. **Status:** Phase-1 gate — partial result.
**Headline:** the n=1 pilot's "coarse is ~2× cheaper than none/medium"
finding **does not survive replication on the easy puzzle.** Fine remains
cleanly separated from coarse; the others overlap.

## Setup

- Puzzle: `puzzle_001` (5×5 easy).
- Conditions: 4 × meta-off only (`none`, `fine`, `medium`, `coarse`).
  meta-on dropped per the pilot finding that the meta axis is inert.
- Two new subset rounds via `harness.run_subset` on 2026-05-08, plus
  pre-existing valid trials from 2026-05-06.
- Model: `claude-opus-4-7[1m]`, `max_turns=35`, default temperature
  (no temp-axis check this window).
- Solved-only trials counted; 3 rate-limit-aborted runs (~3 s, 0 calls)
  excluded from earlier 2026-05-06 attempts.

Per-trial breakdown (all solved):

| toolset | trial 1            | trial 2            | trial 3            | trial 4            |
|---------|--------------------|--------------------|--------------------|--------------------|
| none    | 4 calls / $1.23    | 3 / $1.29          | 3 / $1.09          | 3 / $0.98          |
| fine    | 65 / $1.45         | 68 / $2.28         | 39 / $1.39         | —                  |
| medium  | 26 / $1.47         | 22 / $1.04         | 26 / $1.16         | 23 / $1.06         |
| coarse  | 24 / $0.56         | 25 / $0.73         | 26 / $1.16         | —                  |

Phase-1 budget consumed this window: **$9.85 / 42.8 min wall**.

## Aggregate

| toolset | n | cost μ ± σ      | calls μ ± σ     | time μ ± σ (s)    |
|---------|---|-----------------|-----------------|-------------------|
| none    | 4 | $1.15 ± $0.14   | 3.2 ± 0.5       | 333.6 ± 35.2      |
| fine    | 3 | $1.71 ± $0.50   | 57.3 ± 15.9     | 355.7 ± 80.8      |
| medium  | 4 | $1.18 ± $0.20   | 24.2 ± 2.1      | 320.5 ± 44.4      |
| coarse  | 3 | $0.82 ± $0.31   | 25.0 ± 1.0      | 233.2 ± 89.2      |

Cost ratios vs coarse (mean ± 1σ overlap test):

| toolset vs coarse | ratio | 1σ intervals    | overlap?         |
|-------------------|------:|-----------------|------------------|
| none              | 1.40× | [1.01, 1.29] vs [0.51, 1.13] | **OVERLAP**      |
| fine              | 2.08× | [1.21, 2.21] vs [0.51, 1.13] | separated        |
| medium            | 1.44× | [0.98, 1.38] vs [0.51, 1.13] | **OVERLAP**      |

## What survived replication, what did not

### Survived
- **Fine is genuinely the most expensive condition** on this puzzle. Even
  with high within-cell variance (CV = 29%), its 1σ interval does not
  reach down to coarse's. The "atomic-primitive flooding" pattern (model
  places every edge with `set_edge`) is a real cost driver.
- **Tool-call patterns persist:** fine is high-call, medium and coarse
  are mid-call (~25), none is single-digit. These are stable across
  trials.
- **All toolsets always solve puzzle_001.** Solve-rate signal is zero on
  this difficulty, as expected.

### Did NOT survive
- **The "coarse is ~2× cheaper than none/medium" claim from n=1 is
  invalidated.** At n=3–4, coarse / medium / none cost intervals overlap
  at 1σ; the rank ordering is preserved in means but is not statistically
  separable on this puzzle.
- **Coarse has surprisingly high relative variance** (CV = 38%). Cost ranged
  from $0.56 to $1.16 — a 2× spread within the same cell. The pilot saw
  the bottom end of that range and treated it as the central tendency.
- **Time scaling is noisier than reported.** Coarse trial spread:
  150.9s → 327.9s. The 150.9s figure that anchored the puzzle_001
  baseline note was the fastest of three observations.

### New observations
- **None is the lowest-variance condition** ($0.14 σ on $1.15 mean,
  CV = 12%). Pure-reasoning cost on an easy puzzle is essentially
  deterministic — the model converges on roughly the same solving
  trajectory each time.
- **Fine call counts vary 39–68.** This is the source of the cost
  variance: when the model commits to placing edges one-at-a-time it
  is consistent within a trial, but different trials choose different
  resolution-orderings.
- **Coarse call count is essentially fixed (24–26).** The cost variance
  comes from output-token variance between calls, not from call count.

## Updated reading of the granularity story

On a 5×5 easy puzzle:

- The interesting axis is **fine vs. all-else**, not the four-way ranking
  the pilot suggested. Fine's atomic-primitive cost is real and
  reproducible. The other three are clustered.
- Pilot's "coarse is the efficiency winner" was driven by one favorable
  trial. Coarse's *expected* cost is ~$0.82, but it can run as high as
  $1.16, which lands it in the same band as none and medium.
- The granularity-cost relationship may not be monotonic. We have:
  none ≈ medium ≤ coarse ≤ fine (where ≤ here means "1σ-overlap with").
  That's a U-or-flat shape, not a monotone gradient.

## Phase-1 gate decision

Plan threshold: **"If the cost ratios survive (e.g. coarse ≤ 0.6 × none
with non-overlapping CIs), proceed."**

- Coarse / none ratio = 0.71×, **with 1σ overlap.** Not at the 0.6×
  threshold; not non-overlapping.
- Strictly per the gate, this is a STOP/REFRAME signal on the easy puzzle.

**Recommendation: do not stop yet — replicate puzzle_002 first.**
The n=1 hard-puzzle data (puzzle_002) showed a much larger absolute gap
(none $5.28 vs coarse $2.32, 2.28× ratio at $2.96 absolute spread).
That gap is more likely to survive replication than the easy-puzzle
$0.33 spread, because the per-trial variance we observed (~$0.30 on
coarse) is a smaller fraction of the absolute spread on the hard puzzle.

If puzzle_002 replication also collapses to overlap, that is the real
stop signal.

## Remaining Phase-1 work

To finish Phase-1's gate cleanly, the next 5h window needs:

1. **2 more puzzle_002 trials per cell × 4 cells = 8 runs at ~$16/cell,
   ≈$32 across multiple windows** (doesn't fit in one window). Schedule
   across 2–3 windows, ~$8 each.
2. **Temperature-variance probe** (one cell, temp=0 vs default, ~3
   trials each ≈ $5). Investigate `claude-agent-sdk` first to confirm
   whether temperature is settable via `ClaudeAgentOptions`.
3. Re-run the aggregator with the puzzle_002 data and decide
   Phase-1 → Phase-2 transition.

## Memory updates needed (after writing this note)

- `cost_ratios_stable_across_difficulty.md` — needs invalidation or
  caveat: at n=3–4 on the easy puzzle, the cost ratios are not
  statistically distinguishable except for fine.
- `none_toolset_scales_steeply.md` — the easy-puzzle anchor of this
  claim is now a 4-trial mean of $1.15, not the n=1 $1.29; the qualitative
  claim ("none flips from cheapest to most expensive as puzzles get
  harder") still holds but is less sharp than the pilot suggested.
