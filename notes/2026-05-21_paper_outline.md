# Paper outline (mid-tier archival target)

**Date:** 2026-05-21. **Status:** draft outline, populates as Phase-2
data lands.
**Predecessors:** [`2026-05-21_phase2_design.md`](2026-05-21_phase2_design.md).

## Working title

> Tool-Granularity, Formal Difficulty, and the Cost of LLM Reasoning
> on a CSP Testbed

(Alternative: "When Does Tool Design Reduce LLM Cost?")

## Target venues (in preference order, all archival)

1. **AAAI-27 main track** (preferred). Aug 2026 deadline.
2. **FLAIRS-39** (AAAI Press archival, ~30% accept, Spring 2027).
3. **Archival workshops at NeurIPS-26 / ICML-26** (CEUR / OpenReview /
   `proceedings.mlr.press`). Spring–Fall 2026 deadlines for various.
4. **IJCAI-27** student / short paper track.

The minimum-viable Phase-2 data plus the G-CD model is sized for #2–4.
If the cost-ratio divergence at tier-3 is large enough to be visible
in one figure, #1 becomes defensible too.

## Differentiator vs. *The Tool Illusion* (COLM-2026 scoop)

*Tool Illusion* shows tool sets affect web-agent performance
descriptively. Our differentiators:

1. **Formal CSP testbed.** Slitherlink with a tier-1/2/3+ grader (`core.generator.grade`)
   — difficulty is a *computed* property, not a human label.
2. **G-CD predictive model.** A simple two-term cost decomposition
   that *predicts* when granularity will and won't matter, with
   testable predictions P1–P4. Two predictions already met by Phase-1
   data; P3 and P4 are the Phase-2 tests.
3. **Cost/tool-call decoupling finding.** `fine` does 121 calls for
   the same cost as `none`'s 2 calls. This is the load-bearing
   surprise: tool calls per se are nearly free; what costs is the
   reasoning token volume between them.
4. **Contamination control.** Phase-2 frontier puzzles are
   procedurally generated with seed-locked uniqueness verification.

## Section plan (6–8 pages)

### 1. Introduction (1.5 pp)
- LLM tool use is hot but evaluated descriptively
- Scoop acknowledgement; positioning
- Three contributions (above)
- Roadmap

### 2. Background and related work (1 pp)
- MCP + agentic tool calling (brief)
- Slitherlink as a CSP family with a clean difficulty hierarchy
- Cite *Tool Illusion* + tool-use evaluation literature from
  `notes/related_work.md`

### 3. The G-CD cost model (1 pp)
```
   C ≈ α · n_calls(G, D) + β · n_reasoning_tokens(G, D)
```
- G = granularity (none / fine / medium / coarse)
- D = formal difficulty tier (1 / 2 / 3+)
- Granularity controls the **partition** of work
- Difficulty controls the **floor**
- Derive predictions P1–P4

### 4. Experimental design (1 pp)
- Four toolsets (table)
- Difficulty grader (cite `core.generator`, brief algorithm box)
- Harness, MCP servers, judge, run_plan budget/resume semantics
- Contamination control via generated puzzles
- Single model (note this as limitation), n=3 per cell

### 5. Results (2.5 pp)
- 5.1 Phase-1 anchors: puzzle_001 (tier-1, null), puzzle_002 (tier-2,
  coarse/none = 0.55× non-overlapping CIs)
- 5.2 Phase-2 frontier: gen_7x7_s1_00 (tier-3, ratio TBD)
- 5.3 G-CD predictions check: P1 (tier-1 ratio ≈ 1) ✓, P2
  (tier-2 ratio < 1) ✓, P3 (tier-3 ratio ≤ P2 ratio), P4 (calls/cost
  decoupling)
- Figures: (a) cost-ratio surface across tiers, (b) calls vs. cost
  scatter colored by toolset (the P4 figure — load-bearing surprise),
  (c) wall-time secondary

### 6. Limitations + future work (0.5 pp)
- Single model (cross-model interaction = future work)
- Single point per tier (n=1 puzzle per tier-1 and -3)
- Generator slow at >7×7 — left to future work
- Meta-tool axis cost-infeasible on subscription compute (footnote)

### 7. Conclusion (0.5 pp)
- Granularity matters *conditionally on difficulty*
- Tools as bookkeeping are nearly free; the saving comes from
  removing reasoning steps, not from removing tool calls

## Figure plan (populated as data lands)

| # | Description | Source |
| - | --- | --- |
| F1 | Cost-ratio surface (3 tiers × 4 toolsets) | Phase-1 + Phase-2 |
| F2 | Calls vs. cost scatter (P4 — the surprise) | all trials |
| F3 | Difficulty-grader algorithm box | `core.generator.grade` |
| T1 | Tool-set definitions + tool counts | static |
| T2 | Per-cell results (n, calls, cost, time) | aggregate_phase1 + new |

## Writing logistics

- LaTeX, double-column AAAI / FLAIRS template (depending on
  outcome).
- Reproducibility: commit hash + seed list for each generated puzzle
  + the run_plan command line + JSON results (already
  `harness/results/*.json` — keep these on the repo).
- ~~Anonymized supplementary~~ — not needed at mid-tier.

## Triggers to start writing

- Minimum-viable Phase-2 closed (gen_7x7_s1_00 n=3 per cell, ~2 weeks
  out).
- OR: if compute slips and we can't close Phase-2, write up with
  what we have (Phase 1 + 1 frontier trial) and target a workshop
  instead of #1/#2.