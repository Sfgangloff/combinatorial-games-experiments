# Phase-2 design: difficulty-frontier sweep for AAAI-27

**Date:** 2026-05-21. **Status:** design draft, no runs yet.
**Predecessors:** [`2026-05-18_aaai_plan_and_meta_confound.md`](2026-05-18_aaai_plan_and_meta_confound.md)
(Phase-1 gate closed PASS; meta axis dropped).

## What Phase 2 has to deliver

The defensible-novelty triad after the COLM-2026 *Tool Illusion* scoop
(see predecessor): (i) **formal-difficulty CSP testbed**, (ii)
**model×granularity interaction**, (iii) **predictive theory**. Phase
2 is the empirical backbone that makes (i) and (iii) defensible; (ii)
is a stretch goal addressed below.

Phase-1 gave one data point per difficulty band: easy (puzzle_001, CIs
overlap — null) and hard (puzzle_002, coarse/none = 0.55× non-overlap
— signal). Phase 2 has to show the cost-ratio surface as a function
of formal difficulty, not just two anecdotes.

## Compute reality check

- Today is 2026-05-21. AAAI-27 main-track deadline ≈ 2026-08 → **~12
  weeks**, of which writing/figures need ~2–3 weeks. **≤ 10 weeks of
  compute.**
- 1 window ≈ $8–10, ~1–2 windows/day with babysitting. Absolute
  ceiling ~$650 over 10 weeks. Practical target: **≤ $250**, leaving
  headroom for re-runs and the inevitable limit-mid-trial burns
  (cf. W4/W5/W8/W9 cost $20.57 + $18.61 — limit-burns are now
  budgeted at ~10% overhead).

## Sweep matrix (scoped to fit)

**Publishing ceiling lowered (see memory):** mid-tier archival is
fine. Minimum viable Phase-2 = single frontier tier-3 puzzle with
n=3 per toolset, anchored by Phase-1 puzzle_001 (tier-1 / null) and
puzzle_002 (tier-2 / signal).

| Tier | Puzzle id        | Source                        | Grid | Status |
| ---  | ---              | ---                           | ---  | ---    |
| 1    | puzzle_001       | manifest                      | 5×5  | n=3 (all 4 toolsets) ✓ |
| 2    | puzzle_002       | manifest                      | 7×7  | n=3 (all 4 toolsets) ✓ |
| 3    | gen_7x7_s1_00    | core.generator s=1 tier=3     | 7×7  | 0 / 12 (READY) |
| 3+   | gen_NxN_sK_00    | generator (stretch)           | 8–10 | aspirational; 9×9/10×10 generator runs ran ~14 min CPU with no output and were killed 2026-05-21. **Formal tier-3 generation is computationally expensive at larger grids** — itself a finding worth a sentence in the paper. |

Toolsets: `none, fine, medium, coarse`. **`scratchpad` is intentionally
excluded from the Phase-2 main matrix** — it's a hybrid design move,
not a pure granularity, and folding it in confuses the granularity
claim. It stays in an appendix sweep (existing n=2 on puzzle_002).

**Minimum viable Phase-2 (the bar we're driving to first):**
gen_7x7_s1_00 × 4 toolsets × n=3 = **12 trials**, predicted $57.75
(`run_plan _COST_TABLE`), ~8 windows ≈ **~2 weeks** at 1 window/day.
This is enough — combined with the Phase-1 puzzle_001 (null) +
puzzle_002 (signal) anchors — to claim the tier-1/tier-2/tier-3 cost-
ratio surface in a mid-tier archival paper.

**Stretch: add 8×8 tier-3 puzzle.** 12 more trials (~$65, ~2 more
weeks). Strengthens P3 by having a second tier-3 data point at a
different grid size. Only after the minimum viable Phase-2 closes.

## Theory section (predictive)

Sketch — the falsifiable model the paper would propose and the data
would test. Not finalized, included so Phase-2 puzzle/tier choice
makes sense.

**Granularity-cost decomposition (G-CD).** For a fixed task and model,
total cost decomposes as

```
  C  ≈  α · n_calls(G, D)  +  β · n_reasoning_tokens(G, D)
```

where `G` is the toolset granularity and `D` is the formal difficulty
(tier). The granularity `G` controls the **partition** of work between
the two terms — `fine` pushes work into `n_calls`, `none` into
`n_reasoning_tokens`. Difficulty `D` controls the **floor** of total
work via search depth (tier-1 = propagation only, no search; tier-3 =
non-trivial search nodes). Predictions:

- **P1 (already seen).** At tier-1 (easy), C is dominated by overhead
  and toolset cost ratios collapse to ≈ 1 (puzzle_001 result). ✓
- **P2 (already seen).** At tier-2, coarse beats none by a
  cost-meaningful factor (puzzle_002, ratio 0.55×). ✓
- **P3 (Phase-2 test).** At tier-3, coarse/none ratio is **smaller
  than 0.55×** (or stable, but not larger), because the search-depth
  floor pushes reasoning_tokens up sharply for `none` while
  propagation tooling amortizes well.
- **P4 (Phase-2 test).** `fine` n_calls scales roughly linearly in
  difficulty tier, but its *cost* doesn't, because tool-call cost is
  dominated by reasoning tokens, not calls — the 121-calls-for-same-
  cost-as-2-calls observation is itself the load-bearing finding.

This is the predictive-theory contribution: 1 page of derivation +
the Phase-2 data fit (one scatter plot per prediction). It's narrow
but it's defensible and it's something *Tool Illusion* doesn't have.

## Contamination control

- puzzles 001/002 stay as **anchor / sanity-check** points; the paper
  flags them as potentially-public-source but uses them only to
  validate that the generator-graded tier ordering matches their
  human-labeled difficulty (a *consistency* check, not the headline).
- All Phase-2 frontier results (`gen_t3*`) are on **freshly-generated,
  seed-locked, uniqueness-verified puzzles** — by construction not in
  any model's pretraining corpus, since they didn't exist before
  generation. The generator code + seeds + emitted manifest are
  committed before runs start. Reviewer-defensible contamination
  claim.

## Risk / pivot

- **R1: tier-3 generated puzzles unexpectedly solve cheaply across
  all toolsets** ⇒ G-CD prediction P3 collapses, granularity claim
  weakens further. *Pivot:* lean harder on the cost/tool-call
  decoupling finding (P4) which is independent of P3.
- **R2: tier-3 generated puzzles unsolvable across the board** ⇒ no
  data, just bails. *Pivot:* generate intermediate tier-2.5 puzzles
  (lower clue density at smaller grids).
- **R3: rate-limit chains cost > 20% overhead** ⇒ budget breach.
  *Mitigation:* the existing run_plan abort-on-fatal logic is the
  defense; track cumulative burn in the window log.
- **R4: AAAI deadline slips.** *Accepted.* All work is structured so
  ICML/NeurIPS is a clean fallback — no design choice is AAAI-
  specific.

## Critical path (next runs)

**Prereqs (DONE 2026-05-21):**
1. ✓ Generated gen_7x7_s1_00 (7×7, seed 1, tier-3, 4547 search nodes,
   13 clues). 9×9 and 10×10 attempts killed after 14 min CPU with no
   output — generator too slow at that scale, deferred to stretch.
2. ✓ Manifest entry added (`puzzles/manifest.json`).
3. ✓ Cost table updated (`harness/run_plan.py:_COST_TABLE`). Initial
   guesses revised after first window.
4. ✓ `meta=True` cells stripped from `harness/conditions.py`. The
   `--meta-probe` CLI still works for isolated runs.

**First Phase-2 window:**

```
.venv/bin/python -m harness.run_plan --puzzle gen_7x7_s1_00 \
    --window-budget 8 --max-turns 200
```

Round-robin via `_build_remaining`: cheapest-first per round, so the
first window does coarse + medium (the two cheapest cells at $3.25 +
$4.00 = $7.25). Round 2 picks up the next cheapest cells. ~8 windows
to finish all 12 trials (~2 weeks at 1 window/day).

**After the minimum viable Phase-2 closes:** compute tier-3 cost
ratios with 1σ CIs, fit the G-CD predictions P1–P4 against the full
(puzzle_001, puzzle_002, gen_7x7_s1_00) cost-ratio surface, and
**start writing**. Don't gold-plate — the lowered ceiling means
ship-the-paper beats expand-the-matrix.

## Stretch goals (only if Phase 2 closes early)

- **Second model on a subset.** Re-run `gen_t3a × {none, coarse} ×
  n=3` with Haiku (or Sonnet) = 6 trials, ~$6 total (smaller model
  cheaper). Single data point of model×granularity interaction —
  enough for one figure and a "future-work multi-model sweep" pitch.
- **One scratchpad-on-generated-puzzle sweep.** Adds the
  granularity-with-bookkeeping comparison back in. 3 puzzles × n=1 ≈
  3 trials.

## Decision rule for pivot at end of Phase 2

- Coarse/none cost ratio at tier-3 < 0.55× (predicted) AND CIs non-
  overlapping → **submit to AAAI-27** with G-CD theory + 5-puzzle
  data + contamination control as the package.
- Ratio collapses at tier-3 → **pivot** to the cost/tool-call
  decoupling angle (P4 alone). Still publishable but reframes the
  paper.
- Tier-3 puzzles unsolvable across the board → **regenerate** at
  tier-2.5 and re-run; the predictive-theory section adjusts to the
  achievable difficulty range.
