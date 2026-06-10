# Reasoning externalization: the mechanism behind the Goldilocks cost curve

2026-06-10. Analysis on **existing** solved trials — no new compute.
Reasoning node: `e-0011` → `a-0015` (H-EXT), answering `q-0012`, in the
`slitherlink-tool-granularity` stream.

## Why

Phase-2 (a-0013) established the Goldilocks dollar story: granularity reduces
solving cost only at intermediate difficulty. a-0012 narrowed the cost driver
to *reasoning tokens, not tool calls*. But neither said **how** granularity
moves cost. Total cost factors as `cost ≈ turns × ($/turn)`, so a dollar effect
could be fewer turns, cheaper turns, or both. The existing result records carry
`num_turns`, `total_cost_usd`, and `usage.output_tokens` — enough to decompose
it for free.

## What the data says (Opus 4.7, solved trials, n=3–4/cell)

The decomposition flips the naive intuition. Granularity does **not** reduce
round-trips — it multiplies them:

| rung | turns(none) | turns(tools) | out_tok none/coarse | cost gap none−coarse |
| --- | --- | --- | --- | --- |
| puzzle_001 (96) | 4.2 | 25–58 (≈8.6×) | 1.8× | $0.33 |
| puzzle_002 (501) | 3.3 | 47–122 (≈22.8×) | 2.8× | **$2.16** |
| gen_7x7_s1_00 (4547) | 3.3 | 30–83 (≈16×) | 1.3× | $0.01 |

- **EXT1.** `none` solves in 3–4 turns at every rung; tools take 8–23× as many.
- **EXT2.** `none` generates up to 2.8× more output tokens than `coarse`.
- **EXT3.** The dollar gap `none − coarse` peaks at the mid rung (coarse/none =
  0.71 / **0.55** / 1.00).

## The claim (H-EXT)

**Tool granularity externalizes reasoning.** The no-tools agent compresses
solving into a few token-heavy turns (it generates the whole deduction chain);
a tooled agent spreads it over many token-light turns (one deduction per
round-trip, offloaded to the tool). Granularity trades the first regime for the
second. Whether that is cheaper in dollars is the Goldilocks question:

- **Easy rung:** the no-tools baseline is already cheap (few short turns), so
  there is little to externalize → small gap.
- **Mid rung:** in-context reasoning blows up ($4.75, 172k output tokens for
  `none`); externalizing it into cheap tool turns roughly halves the cost →
  largest gap.
- **Hard rung:** the tool agent needs many turns, and each turn re-reads a
  growing transcript (cache-read context cost). That per-turn context tax eats
  coarse's advantage → the gap collapses back toward zero.

So the turn/token trade is **monotone** in granularity, but the *dollar* benefit
is **single-peaked** — a Goldilocks zone that falls out of the interaction
between externalization (helps) and context re-read cost (hurts, and grows with
difficulty). This is the mechanism under a-0013, and it sharpens a-0012 from
"reasoning tokens cost" to "granularity relocates reasoning tokens into turns,
at a per-turn context price."

## Falsifiers / next checks

- **Per-turn context tax.** EXT3's hard-end collapse is *attributed* to
  cache-read growth across many turns; verify directly by reading
  `usage.cache_read_input_tokens` per turn vs cumulative (the records carry it).
  If cache-read does not grow with turns on gen_7x7, the proposed hard-end
  mechanism is wrong.
- **Generality.** Opus-only, three rungs, n=3–4. The model × granularity sweep
  (e-0010) would show whether the externalization ratio and the gap-peak
  location shift with model capability (a weaker model may externalize more,
  earlier).
- **Single-peak robustness.** EXT3 rests on three points. A fourth mid–high rung
  (e.g. gen_7x7_s3_00 once it has a solved `none` trial) would test whether the
  peak is real or an artifact of puzzle_002.

## How to run

```bash
python -m harness.analyze_efficiency_frontier            # tables + EXT1/2/3
python -m harness.analyze_efficiency_frontier --meta on  # meta-on cells instead
```

## Files

- `harness/analyze_efficiency_frontier.py` — the decomposition + EXT1/2/3 checks.
