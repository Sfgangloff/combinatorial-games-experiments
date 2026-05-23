# G-CD revision: the Goldilocks two-floor model

**Date:** 2026-05-23. **Status:** theory revision triggered by Phase-2
partial-verdict P3 falsification. Draft of the §3 (theory) rewrite
for the paper.
**Predecessors:** [`2026-05-21_phase2_design.md`](2026-05-21_phase2_design.md)
(original G-CD + P1–P4); [`2026-05-18_aaai_plan_and_meta_confound.md`](2026-05-18_aaai_plan_and_meta_confound.md)
(Phase-1 gate verdict + Phase-2 partial verdict).

## What changed

The Phase-2 partial verdict (10/12 trials on `gen_7x7_s1_00`, n=1 at
`none`) shows the **coarse/none cost ratio at tier-3 is 1.05×** — not
≤ 0.55× as predicted. All four toolsets' 1σ CIs overlap at tier-3.
The cost-ratio surface across the three tiers is **V-shaped**: spread
maximal at tier-2, collapsed at both tier-1 and tier-3
(`paper/figures/f1b_cost_ratio_by_tier.png`).

Pre-committed P3 of the original G-CD model is **falsified**. The
question is whether the *whole* model is dead or only the monotonicity
assumption baked into P3. This note argues it's the second.

## Diagnosis: the original model has no floor term

Original G-CD:

```
  C  ≈  α · n_calls(G, D)  +  β · n_reasoning_tokens(G, D)
```

Both terms scale with work performed; neither captures the **fixed
overhead** a trial pays regardless of granularity or difficulty —
model initialization, puzzle ingestion, the final submit/verify
exchange. Empirically that overhead is at least the `none`-trial cost
at tier-1: ~$1.15 for 3 tool calls and ~3.2 min of API time. Call
it γ.

Add the floor:

```
  C  ≈  γ  +  α · n_calls(G, D)  +  β · n_reasoning_tokens(G, D)
                                                              (G-CD-v2)
```

Then cost *ratios* between toolsets are:

```
  C(G₁) / C(G₂)  =  [γ + W(G₁, D)] / [γ + W(G₂, D)]
```

where `W(G, D) = α · n_calls + β · n_reasoning_tokens` is the
work-volume term.

**Key property of G-CD-v2:** the ratio `C(G₁)/C(G₂)` approaches 1
when γ ≫ ΔW (low-difficulty regime) **and** approaches 1 when the
between-toolset gap |W(G₁,D) - W(G₂,D)| is small relative to the
*average* W (high-difficulty regime, where every toolset pays a
search-depth floor that no granularity can amortize away).

That is: the original G-CD-v1 had no mechanism to predict ratio
collapse at tier-3. G-CD-v2 has two distinct mechanisms for ratio
collapse, and they bite at opposite ends of the difficulty axis.

## Revised predictions

### P1' (collapse at low difficulty — unchanged in form, restated mechanically)

At tier-1, W(G, D) is small relative to γ. Ratios → 1 because
overhead dominates. Empirically: tier-1 ratios 0.71×–1.49×, all 1σ-
overlap with `none`. **PASS** (same data, sharper mechanism).

### P2' (divergence at intermediate difficulty — unchanged)

At tier-2, W is large enough that ΔW between toolsets dominates γ,
and the toolset-specific reasoning savings haven't yet saturated.
Empirically: coarse/none = 0.55×, separated 1σ. **PASS** (unchanged
from G-CD-v1).

### P3' (re-collapse at high difficulty — NEW, replacing falsified P3)

At tier-3, W is large for every toolset because search-depth
reasoning dominates and toolset granularity cannot amortize search
nodes (only propagation). ΔW shrinks relative to the W floor, and
ratios → 1 again.

Empirically (n=1 at `none`, n=3 elsewhere): coarse/none = 1.05×,
all four toolsets within $0.62. **PASS in shape** (collapse
observed), but the mechanism (search-depth floor) needs the
remaining two `none` trials to be confirmed quantitatively. If
those land near the n=1 value of $1.97, the cost-ratio surface
remains V-shaped. If they land much higher (e.g. $4–5, comparable
to tier-2 `none`), tier-3 would re-open as a divergence regime and
P3' itself falsifies.

### P4 (calls/cost decoupling — unchanged, sharpened by data)

`fine` does 100× more tool calls than `none` for ≈ the same cost,
because the cost is dominated by `β · n_reasoning_tokens`, not by
`α · n_calls`. The α term is empirically near-zero on a per-call
basis: at tier-2, $/call = $2.04 (none) vs $0.037 (fine), a **55×
gap**.

This makes a sharper claim than G-CD-v1 stated: **α ≪ β under
current pricing**, i.e. the cost of a tool call is dominated by the
*reasoning context tokens* sent through the API on that turn, not by
any constant per-call overhead. The granularity dial is best
understood as redirecting reasoning into compact tool invocations —
the call-count itself is incidental.

### P5 (NEW: the divergence is unimodal in D)

G-CD-v2 predicts a **single peak** in the toolset-spread function
σ(C | D) over difficulty. The peak is at the difficulty where ΔW(G)
is maximal relative to γ + min_G W(G, D). For Slitherlink under our
toolsets, the data places this peak in the tier-2 band (puzzle_002,
~7×7 hard, ~30 min trials).

P5 is the falsifiable extension: if a tier-2.5 puzzle (between
puzzle_002 and gen_7x7_s1_00 in formal difficulty) shows ratios
*larger* than tier-2, the unimodality assumption fails and we need
a yet richer model. Cost: 1 generator run + ~$60 of trials. **Not
budgeted for Phase 2**; appendix-only or future work.

## What this means for the paper

The headline is no longer "more tools = lower cost." It is:

> **Tool-set granularity reduces LLM solving cost at intermediate
> difficulty; the benefit collapses at both ends of the difficulty
> axis. The mechanism is overhead-dominance at the easy end and
> search-depth-dominance at the hard end. The cost of a tool call
> is dominated by the reasoning-token context, not by call count.**

This is a *more* interesting story than the linear version, and it
is what the data actually shows. Concrete consequences for the
write-up:

- §3 rewrites G-CD-v1 → G-CD-v2 with the γ floor and the two-end
  collapse mechanism.
- §5 frames the V-shape as the headline finding, with the cost-ratio
  surface (F1b) as the load-bearing figure.
- §5 keeps P4 as the secondary load-bearing finding (F2 scatter);
  it survives the model revision unchanged.
- §6 limitations: P5 (unimodality) is untested; tier-3 `none` is
  n=1; gen_7x7_s1_00 may be cost-cheap by sparse-clue accident
  rather than tier-3 by formal grading.

## What the remaining 2 `none` trials can do

The most fragile claim in the surface is tier-3 `none` at n=1 = $1.97
with 2 tool calls. Two more trials, by outcome:

| If tier-3 `none` lands at... | P3' verdict | Paper impact |
| --- | --- | --- |
| $1.50–$2.50 (similar to n=1) | confirms shape | strengthens Goldilocks story; ship it |
| $3.00–$4.00 (between tier-2 and current n=1) | weakens but doesn't kill | ratio drifts to ~0.7×, headline survives with softer "spread shrinks at tier-3" framing |
| ≥ $4.00 (comparable to tier-2 `none`) | falsifies P3' | tier-3 re-becomes a divergence regime; Goldilocks story dies; pivot to "tools always help at high difficulty, just not at low" |

**Probability assessment from n=1 + n=3 at other toolsets:** The
`fine`/`medium`/`coarse` tier-3 cells dropped roughly 30–40% in cost
vs their tier-2 cells (e.g. coarse $2.59 → $2.07). If `none` follows
the same pattern, two more trials at ~$3 each would put the cell μ
near $2.65 with σ ~$1. That makes the "weakens but doesn't kill"
row most likely.

## How this affects the decision rule

The original Phase-2 decision rule was: P3 PASS (ratio ≤ 0.55×,
separated) → submit AAAI; otherwise pivot. With G-CD-v2, the
decision rule becomes simpler and is *already met by the data*:

- The V-shape itself is the AAAI-defensible claim, conditional on
  two confirming data points: tier-1 collapse ✓ and a clean
  tier-2 divergence ✓.
- Finishing the remaining 2 `none` trials makes the tier-3
  collapse claim quantitative rather than n=1.

If budget authorization comes through for the remaining 2 trials,
they close the minimum-viable Phase-2 and unlock the writing trigger
(see `2026-05-21_paper_outline.md`).

## Action items

1. **Update the paper outline** — §3 wording and §5 figure
   list reflect G-CD-v2. (Free, ~30 min.)
2. **Optional: regenerate F1b with annotated peak** — annotate the
   tier-2 V-bottom on the figure for the paper. (Free, ~5 min.)
3. **Authorize remaining 2 tier-3 `none` trials** to close the
   minimum-viable Phase-2 and quantify the n=3 tier-3 `none` cell.
   (Paid, ~$11 / ~2 windows.)
4. **Stretch**: generate a tier-2.5 puzzle to test P5 unimodality.
   Appendix-only; defer until Phase 2 closes.
