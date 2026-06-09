# Model × granularity: does the Goldilocks zone shift with capability?

2026-06-09. Design note for the next experiment block. Status: code landed,
trials not yet run (needs an authorized window).

## Why

The Phase-2 thesis (a-0013 in the reasoning graph) is the **Goldilocks model**:
tool-set granularity reduces LLM solving cost *only at intermediate difficulty*
— the benefit collapses at both ends (overhead-dominated when easy, search-floor
dominated when hard). The G-CD-v2 cost model formalizes it.

But every trial behind that thesis ran on **one model**: Opus 4.7 (the SDK
default — the result records show `claude-opus-4-7[1m]` even when `model: null`
was requested). One of the three original novelty pillars (a-0001) was a
**model × granularity interaction**, and it was never actually tested.

The natural prediction: "intermediate difficulty" is not absolute — it's
**relative to the model's own frontier**. A weaker model hits its intermediate
zone on an *easier* puzzle, so coarse tools should help it where they did
nothing for Opus. If so, the Goldilocks band is a **diagonal** in the
(capability × difficulty) plane, not a vertical stripe:

```
            easy        mid         hard        ceiling
  Haiku    [helps]      ----        ----        xxxx
  Sonnet    ----       [helps]      ----        xxxx
  Opus      ----        ----       [helps]      xxxx
```

This reframes the headline from "granularity helps at intermediate difficulty"
to "granularity helps when difficulty ≈ the model's frontier" — a sharper,
more general, and more defensible claim for AAAI-27.

## Hypotheses (testable)

- **MG1 (shift).** The difficulty rung at which the granularity benefit
  (cheapest-toolset cost ÷ `none` cost) is largest *increases* with model
  capability. Operationalized: peak-benefit `search_nodes` is non-decreasing
  across Haiku → Sonnet → Opus, and strictly increasing for at least one step.
- **MG2 (left-shift of help).** On a puzzle where granularity did *not* separate
  from `none` for Opus (e.g. the easy/low-node 7×7 rungs), it *does* separate
  (best band below `none` at 1σ) for a weaker model.
- **MG3 (ceiling tracks capability).** The difficulty at which all toolsets fail
  (the solve-rate cliff) is lower for weaker models — Haiku's "15×15 wall" comes
  earlier on the ladder than Opus's.

A clean falsifier: if the peak-benefit difficulty is flat or non-monotone across
models, the simple capability-relative story is wrong (granularity benefit would
then be a property of the *task*, not the model–task gap).

## Design

- **Models (capability ladder):** `claude-haiku-4-5` < `claude-sonnet-4-6` <
  `claude-opus-4-7` (the existing baseline, reused as the strong anchor via
  `--include-default`). Opus 4.8 can be added later as a top rung.
- **Difficulty ladder (fixed 7×7 size, so difficulty varies independent of board
  size):** `puzzle_002` (~501 nodes) → `gen_7x7_s3_00` (3789) → `gen_7x7_s1_00`
  (4547), with `puzzle_001` (5×5, ~96 nodes) as the easy anchor. `puzzle_004`
  (15×15) stays as the shared ceiling for the MG3 solve-rate probe.
  *Optional lower 7×7 rung* (cleaner left end for MG2, all-7×7): generate one
  with `python -m core.generator --rows 7 --cols 7 --seed <S> --min-tier 1
  --out-dir puzzles --emit-manifest` and pick a low-`search_nodes` result.
  (7×7 grades are slow — each is a full backtracking count — so generation can
  take a few minutes per puzzle.)
- **Toolsets:** none / fine / medium / coarse, meta-off, n≥3 per cell (same
  protocol as Phase-1/2 so the 1σ overlap test carries over).
- **Metric:** per (model, puzzle, toolset) cost μ±σ; benefit = 1 − (cheapest
  toolset ÷ none); "separated" = best band below none's band at 1σ.

## How to run

```bash
# Plan is always free — start here:
python -m harness.run_model_grid --dry-run --include-default \
    --models claude-sonnet-4-6 claude-haiku-4-5 \
    --puzzles puzzle_001 puzzle_002 gen_7x7_s3_00 gen_7x7_s1_00 \
    --toolsets none fine medium coarse --n 3

# Authorize a window, then run (resumable across windows):
export BUDGET_AUTHORIZED=1
python -m harness.run_model_grid --include-default ... --window-budget 8

# Analyze (model-aware; tests MG1):
python -m harness.analyze_model_x_granularity
```

The runner reuses the existing Opus-4.7 baseline trials for the anchor cells
(they show `3/3` in the dry-run), so only the Sonnet/Haiku cells cost new money.
Weaker models are cheaper (≈0.6× Sonnet, ≈0.25× Haiku of Opus per the priors in
`run_model_grid._MODEL_COST_MULT`), so the full sweep is far cheaper than an
equivalent all-Opus block.

## Guardrail note

The bash hook (`.claude/hooks/check_bash.sh`) only budget-gates
`harness.run_plan`. `run_model_grid` *also* spends real compute, so it carries
its **own** `BUDGET_AUTHORIZED=1` gate (refuses live runs without it; `--dry-run`
is always free). For defense in depth, consider adding a
`*"python -m harness.run_model_grid"*` case alongside the `run_plan` case in the
hook so the gate is enforced at the harness boundary too.

## Files

- `harness/run_model_grid.py` — resumable, model-aware sweep runner.
- `harness/analyze_model_x_granularity.py` — groups by (model, puzzle, toolset),
  computes the benefit surface, tests MG1.
- `puzzles/gen_7x7_s*_00.txt` (+ manifest) — the fixed-size difficulty ladder.
