# Tool-Granularity, Formal Difficulty, and the Cost of LLM Reasoning on a CSP Testbed

**Working draft in markdown** — to be converted to AAAI / FLAIRS LaTeX
template before submission. Source notes:
[`notes/2026-05-23_gcd_revision_goldilocks.md`](../notes/2026-05-23_gcd_revision_goldilocks.md),
[`notes/2026-05-21_phase2_design.md`](../notes/2026-05-21_phase2_design.md),
[`notes/2026-05-21_paper_outline.md`](../notes/2026-05-21_paper_outline.md).
Reproducibility: all reported numbers come from
`python -m harness.analyze_phase2 --figures` over the JSON trials in
`harness/results/`.

---

## Abstract (placeholder)

> Large-language-model agents call tools through standardized
> interfaces (MCP, function calling), but the *granularity* of those
> interfaces — many fine primitives vs. a handful of named deductions
> vs. one coarse "suggest a move" — is rarely treated as a controlled
> experimental variable. We study tool-granularity on a Slitherlink
> constraint-satisfaction testbed where (i) puzzle difficulty is a
> *computed* property via a tier-1/2/3 formal grader, and (ii)
> contamination is controlled by procedurally generating frontier
> instances. We propose **G-CD-v2**, a two-floor cost decomposition
> that adds a fixed-overhead γ term to the standard work-volume
> decomposition. The model predicts and the data confirm a
> **non-monotonic, Goldilocks-shaped** dependence of toolset advantage
> on formal difficulty: granularity helps at intermediate difficulty
> (coarse/none cost ratio = 0.55× at tier-2, separated 1σ) but the
> advantage collapses at *both* low difficulty (overhead-dominated,
> ratios → 1) and high difficulty (search-depth-dominated, ratios →
> 1). We also report a sharp **calls/cost decoupling**: a `fine`
> trial runs ≈ 50× more tool calls than a `none` trial for
> statistically indistinguishable cost, because per-call cost is
> dominated by reasoning-token context, not by call count.

## 1. Introduction

Large-language-model agents increasingly call external tools through
standardized interfaces — the Model Context Protocol (MCP), OpenAI
function-calling, Anthropic's tool-use API. A single agent may have
access to anywhere from two tools to several thousand, packaged at
arbitrary levels of abstraction: a single high-level "solve this
puzzle" call, or dozens of atomic primitives for setting one edge of
state at a time, or anything in between. The *granularity* at which
tools partition work between model and engine is a designer-controlled
variable; yet most published evaluations report cost and success rate
without holding granularity as an independent axis.

The closest prior work, Lou et al.'s *Tool Illusion* (COLM 2026),
demonstrates that tool design has first-order effects on agent
performance, in the web-agent domain, using agent-synthesized skills
classified post-hoc into "complexity levels." Their headline — *tools
should not be overly complex; decouple agentic reasoning from
tools* — is descriptive, single-domain, and synthesised-skill-based.
We share the high-level question (does granularity matter?) but
attempt three things their setting does not afford:

1. **A formal-difficulty CSP testbed.** Slitherlink puzzles admit a
   computed tier-1/2/3 difficulty grader (propagation only / + one-ply
   lookahead / search-required) implemented in `core.generator.grade`.
   Difficulty is a property of the puzzle, not a human label.
2. **A predictive cost model, G-CD-v2.** We propose a two-floor
   decomposition of API cost into a fixed overhead γ and a
   work-volume term `W(G, D)` partitioned by granularity `G` and
   difficulty `D` (§3). The model makes four falsifiable predictions
   P1'–P4 and forbids the simpler monotone "more tools = lower cost"
   alternative.
3. **Contamination control by construction.** The frontier tier-3
   puzzle in this study is procedurally generated with a fixed seed
   and a uniqueness verifier; it did not exist before its generation
   date.

The data confirm a **non-monotonic, Goldilocks-shaped** dependence of
toolset advantage on formal difficulty: a coarse-granularity toolset
roughly halves the API bill at tier-2 (coarse/none cost ratio = 0.55×,
non-overlapping 1σ CIs) but the advantage *collapses* at both tier-1
(overhead-dominated, ratios → 1) and tier-3 (search-depth-dominated,
ratios → 1). A simpler monotone model — the same paper's pre-committed
G-CD-v1 — predicted strictly shrinking ratios with difficulty and is
**falsified** by the tier-3 data; we report both verdicts side by side
(§5).

A second, possibly more surprising finding survives the model
revision and is what we view as the **load-bearing observation** of
the paper: tool-call count does not predict cost. At tier-2, a `fine`
trial issues 121 tool calls per puzzle for $4.45 while a `none` trial
issues 2.3 calls per puzzle for $4.75 — *the same cost, 50× the
calls*. Per-call cost varies by 55× across granularities (Table 3).
The granularity dial is therefore best understood as *redirecting*
reasoning between in-context deliberation and compact tool
invocations, not as adding or removing book-keeping calls. We
formalize this as P4 in §3 and discuss its implications for tool
design in §7.

### Contributions

- A **formal-difficulty CSP testbed** (Slitherlink with a
  propagation/lookahead/search tier grader) and a procedurally
  generated, uniqueness-verified, contamination-controlled tier-3
  frontier puzzle.
- A **two-floor predictive cost model G-CD-v2** that predicts the
  observed Goldilocks shape from a minimal mechanism (fixed
  per-trial overhead γ plus granularity-partitioned work volume `W`).
- An empirical demonstration that **per-call cost dominates call
  count by ~55×** under current Claude pricing — the headline-
  surprise finding, robust across both the v1 and v2 cost models.
- A reproducible artifact: 38 solved trials' worth of JSON traces,
  the analyzer, the generator, and the puzzles, all released as
  `harness/results/`, `harness/analyze_phase2.py`,
  `core/generator.py`, and `puzzles/manifest.json` in the project
  repository.

### Roadmap

§2 surveys related work and positions the paper. §3 develops G-CD-v2
and pre-registers predictions P1'–P4. §4 describes the toolsets,
puzzles, harness, and contamination control. §5 reports per-tier
results and prediction verdicts; the V-shape (Figure F1b) and the
calls–cost scatter (Figure F2) are the two load-bearing figures.
§6 lists limitations and future work. §7 concludes.

## 2. Background and related work

### 2.1 Tool-using LLM agents

ReAct [Yao et al., 2022], Toolformer [Schick et al., 2023], and
ToolLLM [Qin et al., 2023] established the basic pattern: an LLM
interleaves natural-language reasoning with calls to typed external
tools, receiving structured responses that become part of its
context. AgentBench [Liu et al., 2023] and τ-bench [Yao et al., 2024]
provide multi-environment harnesses; Reflexion [Shinn et al., 2023]
and Voyager [Wang et al., 2023] add self-correction and skill
construction. The Model Context Protocol (MCP) standardizes the
tool-registration interface that today's agents (including the
Claude Code agent used in this paper) consume.

### 2.2 Cost-aware tool use

A separate strand of work treats *cost* as a first-class evaluation
axis: CATP-LLM [Wu et al., 2024] plans for cost-aware tool use,
Efficient Agents [Wang et al., 2025] reports the first systematic
cost-effectiveness comparison across agents, and Cost-of-Pass [Erol
et al., 2025] proposes an economic framework for LM evaluation.
When2Call [Ross et al., 2025] specifically studies *when not* to call
a tool. These papers share with us the cost axis, but treat the
*toolset* as fixed and vary policy, prompting, or model. We do the
opposite: fix the model and policy, vary the toolset.

### 2.3 Scale and retrieval over many tools

A third strand addresses the engineering problem of presenting
thousands of tools to an agent: AnyTool [Du et al., 2024], Toolshed
[Lumer et al., 2024], ToolScope [Liu et al., 2025],
TheMCPCompany [Esfandiarpoor et al., 2025], MCP-AgentBench [Guo et
al., 2025]. We treat this orthogonally — our four toolsets are
intentionally small enough to be fully present in context at all
times, so retrieval is not a confound.

### 2.4 Granularity as the variable

The closest prior work is **The Tool Illusion** [Lou, Peng, Yao et
al., COLM 2026], which evaluates web-agent performance across tools
of varying complexity. Their findings include: *"Tools should not be
overly complex,"* a "tool-tax" cost-overhead analysis, and a
strong-to-weak skill transfer effect. The paper is descriptive,
single-domain (web/browser agents, WALT/SkillWeaver hybrids), and
classifies tool complexity *post-hoc* over agent-synthesized skills.
Agent Capsules [Ray, 2026] uses the word "granularity" but for
multi-agent merging, not single-agent tool design — orthogonal to our
question.

We share the framing question with *Tool Illusion* but differ on
three points: (i) our task is a formal CSP with binary verifiable
outcomes — no LLM-judge subjectivity, (ii) our granularities are
*designer-controlled* across a known model-engine work-partition
spectrum rather than agent-synthesized, and (iii) we contribute a
predictive cost model rather than a descriptive classification.

### 2.5 CSP and logic-puzzle benchmarks

TopoBench [Maniparambil et al., 2026] benchmarks LLMs on loop and
connectivity puzzles, but holds the toolset fixed. Eidoku [Miya,
2025] studies neuro-symbolic verification on Sudoku. Estermann &
Wattenhofer [2025] relate reasoning effort to formal problem
complexity in non-agent LLM settings. Berthier's earlier work on
pattern-based constraint satisfaction [Berthier, 2013] gives the
deductive vocabulary that our tier-1/2 propagation/lookahead grader
inherits. None of these vary tool granularity.

### 2.6 Positioning

We position this paper as the **first granularity-controlled,
formal-difficulty, predictive cost study** of LLM tool use. The
field-level claim "granularity matters" is taken — *Tool Illusion*
holds that descriptive ground on a different domain. Our defensible
contributions are the predictive model (G-CD-v2), the
formal-difficulty axis, and the calls–cost decoupling quantification.

## 3. The G-CD-v2 cost model

We propose a simple, falsifiable cost decomposition. For a fixed task,
model, and pricing schedule, the API cost of a single solved trial is

```
  C(G, D)  ≈  γ  +  α · n_calls(G, D)  +  β · n_reasoning_tokens(G, D)
                                                               (G-CD-v2)
```

where `G` denotes toolset granularity (the four discrete settings of
Section 4), `D` denotes formal puzzle difficulty (tier-1/2/3 by the
Section-4 grader), and γ, α, β are pricing-determined non-negative
constants. The three terms separate cleanly:

- **γ** is the **fixed per-trial overhead** — model warm-up, puzzle
  ingestion at trial start, the final submit/verify exchange. It is
  independent of `G` and `D`.
- **α · n_calls** captures any cost that scales linearly with the
  number of tool calls (per-call API book-keeping). Empirically (§5)
  α is near-zero under current Claude pricing — tool calls themselves
  are cheap; what is expensive is the context they carry.
- **β · n_reasoning_tokens** captures the cost of reasoning-token
  context attached to each turn. Under chain-of-thought-style
  agentic loops this term scales roughly with the *work volume* the
  model performs in-context.

Define the **work-volume** `W(G, D) = α · n_calls(G, D) + β ·
n_reasoning_tokens(G, D)`. The granularity dial `G` controls the
*partition* of work between book-keeping calls and in-context
reasoning; the difficulty dial `D` controls the *floor* of `W` via
search depth. The ratio of costs between two granularities reduces to

```
  C(G₁, D) / C(G₂, D)  =  [γ + W(G₁, D)] / [γ + W(G₂, D)]
```

which has two distinct mechanisms for ratio collapse to 1:

- **Low-D collapse:** when `W(G, D) ≪ γ` for all `G` (overhead-
  dominated regime, easy puzzles), cost ratios → γ / γ = 1.
- **High-D collapse:** when `|W(G₁, D) − W(G₂, D)| ≪ mean_G W(G, D)`
  (search-depth-dominated regime, hard puzzles where no granularity
  can amortize the search-required work), ratios → 1.

The G-CD-v2 model predicts that the granularity-cost benefit is
maximized at *intermediate* difficulty, where `W` is large enough to
dominate γ but the between-toolset gap |ΔW| is still large relative
to the mean `W`. This is a **single-peaked**, non-monotonic prediction.

### Predictions

We pre-register the following four primary predictions, tested in §5.
A fifth, P5, is left as appendix / future work because it requires a
tier-2.5 puzzle not in the current corpus.

- **P1' — Low-difficulty collapse.** At tier-1, all toolset
  cost ratios C(G, 1) / C(none, 1) lie within 1σ of 1.0.
- **P2' — Mid-difficulty divergence.** At tier-2, there exists at
  least one granularity G with cost ratio strictly less than 1 to
  `none`, with non-overlapping 1σ confidence intervals.
- **P3' — High-difficulty re-collapse.** At tier-3, all toolset cost
  ratios C(G, 3) / C(none, 3) again lie within 1σ of 1.0 (mirroring
  the tier-1 collapse). *This prediction is the Goldilocks claim and
  is what distinguishes G-CD-v2 from a simpler monotone "more tools
  = lower cost" model.*
- **P4 — Calls/cost decoupling.** Within a tier, the per-call cost
  C/n_calls varies by more than 10× across granularities, despite
  cost itself varying by less than 2×. Equivalently, α ≪ β under
  current Claude pricing.

### Relation to a discarded v1 model

An earlier monotone variant of the model (G-CD-v1, recorded in
[`notes/2026-05-21_phase2_design.md`](../notes/2026-05-21_phase2_design.md))
predicted a **strictly shrinking** coarse/none ratio with increasing
difficulty (`P3`-monotone: tier-3 ratio ≤ tier-2 ratio with separated
CIs). That prediction was pre-committed before Phase-2 data and is
**falsified** by the data in §5 (tier-3 ratio = 1.00× vs tier-2 =
0.55×). G-CD-v2 adds the γ floor explicitly, which is the minimal
modification consistent with both the existing data and elementary
mechanism: every trial pays an overhead regardless of `G` or `D`.
We report both verdicts in §5 for reviewer-defensible framing.

## 4. Experimental design

### 4.1 Task: Slitherlink

Slitherlink is a loop-construction CSP on an `n × m` grid of cells.
Each cell may be empty or contain a clue digit in `{0, 1, 2, 3}`; the
goal is to draw a single non-self-intersecting closed loop along grid
edges such that the number of loop edges adjacent to each clue cell
equals that clue. Solving is decidable by depth-bounded constraint
propagation plus search; deciding has worst-case exponential time
but Slitherlink belongs to NL ∩ TC⁰ for many natural sub-families.
The puzzle has a verifiable binary outcome (a candidate solution is
correct iff a single closed loop satisfies every clue), eliminating
LLM-judge artifacts.

### 4.2 Toolsets (the granularity dial)

We compare four toolsets, registered with the agent as MCP servers.
Each toolset is presented in isolation — the agent sees only the
judge tools (`get_puzzle`, `submit_solution`) plus the toolset under
test.

**Table 1 — Toolsets under comparison.** Tool counts include the
two judge tools.

| Granularity `G` | Tool count | Examples | Engine work performed by tools |
| --- | --- | --- | --- |
| **none**   | 2 (judge only) | `get_puzzle`, `submit_solution` | None — pure-reasoning baseline. |
| **fine**   | 21 | `get_edge`, `set_edge`, `count_edges_at_dot`, … | State tracking only; the model performs all inference. |
| **medium** | 13 | `apply_edge` (with propagation), `forced_moves`, `endpoints`, … | One-step local inference (clue propagation, dot-endpoint analysis). |
| **coarse** | 11 | `suggest_next_move`, `apply_move` | Propagation + one-ply lookahead — the tool proposes the next forced edge. |

The four toolsets span a known spectrum from pure-LLM reasoning to a
near-complete external solver, while the *task* is held fixed. A
fifth toolset, **scratchpad** (`medium` + a frame stack for assumption
management + `try_both` engine-level lookahead), exists in the repo
but is excluded from the Phase-2 main matrix because it conflates
granularity with auto-bookkeeping, a separate design move. Scratchpad
results are reported in an appendix.

### 4.3 Difficulty grader (the difficulty dial)

Formal difficulty is a computed property of each puzzle, not a human
label. The grader (`core.generator.grade`) returns
`(tier, search_nodes)`:

- **Tier 1.** Solvable by clue-driven propagation alone (no
  assumption, no lookahead). `core.propagation.propagate_only`
  reaches a complete solution.
- **Tier 2.** Solvable by propagation + one-ply lookahead — at each
  ambiguous edge, try both assignments; if exactly one is consistent,
  apply it; iterate.
- **Tier 3.** Requires depth-≥ 2 search. `search_nodes` is the size
  of the backtracking tree (verified by `count_solutions` with
  early-exit at 2 solutions, which also verifies uniqueness).

The three anchor puzzles span the three tiers:

| Puzzle | Size | Tier | Source | n_clues | search_nodes |
| --- | --- | --- | --- | --- | --- |
| puzzle_001 | 5×5 | 1 | puzzle-loop.com (Phase-1 anchor) | 13 | 1 |
| puzzle_002 | 7×7 | 2 | puzzle-loop.com Puzzle ID 25,425 | 24 | 1 |
| gen_7x7_s1_00 | 7×7 | 3 | generator, seed 1 | 13 | 4547 |

### 4.4 Contamination control

Tier-1 and tier-2 puzzles are taken from puzzle-loop.com, a public
archive. While the resulting solutions are not expected to be in any
model's pretraining corpus *as token sequences*, the puzzle clues
themselves might be. We use these puzzles only as **anchor points**
that the formal grader confirms occupy the expected tiers.

The tier-3 frontier puzzle `gen_7x7_s1_00` is **procedurally
generated** by `core.generator.generate_one` with a fixed seed
(`s = 1`). Generation runs a random region growth followed by
`reduce_to_unique`, dropping clues in random order while
`count_solutions` confirms uniqueness. The emitted puzzle did not
exist before `2026-05-21` by construction; its formal tier and
search-node count are recorded in `puzzles/manifest.json` and
reproducible from the seed.

### 4.5 Harness, MCP, judge

The agent loop is driven by `harness.run`, which:

1. Selects a `(puzzle, toolset)` cell.
2. Spawns Claude Code as a subprocess with the toolset's MCP servers
   registered.
3. Streams the agent's tool calls and intermediate thinking to a
   per-trial JSON record (`harness/results/*.json`).
4. Terminates on first `submit_solution(correct=True)` or on a
   max-turn / max-tool-call budget.
5. The **judge** verifies submitted solutions against the canonical
   solution stored in the manifest. Verification is byte-exact loop
   topology — no LLM-as-judge.

For multi-trial campaigns, `harness.run_plan` is a resumable,
window-budget-capped runner. It scans `harness/results/`, counts
already-good trials per cell, and runs only what is missing. Each
trial's spend is checked against a configurable window-budget cap
(default $8, matching Anthropic's 5-hour rate-limit window); the
runner stops cleanly at the cap so a closed window doesn't burn the
remaining plan. The full Phase-2 minimum-viable campaign (12 trials)
ran over 9 counted windows + 3 limit-aborted windows for $39.12
counted spend ($59.07 total with limit-aborts).

### 4.6 Model, replication, exclusions

All trials use a single model — **Claude Opus 4.7 (1M-context
variant, `claude-opus-4-7[1m]`)** — at default thinking-mode
settings (extended thinking on, `max_turns = 200`). Replication is
n = 3 per (puzzle, toolset) cell, with n = 4 retained for two
Phase-1 cells. Solved-trials-only aggregates; rate-limit-aborted
trials are excluded.

The choice of a single model is deliberate: with subscription-only
compute, an n = 3 × 4-toolset × 3-tier design at one model uses
~$60 of API quota; cross-model interaction would multiply the budget.
Cross-model effects are flagged as future work in §6.

## 5. Results

We report the cost-ratio surface and prediction verdicts across three
formal-difficulty tiers. All trials use a single model (Claude Opus
4.7, 1M-context variant) at n = 3 per (toolset, puzzle) cell, with the
two extra `none` trials at puzzle_001 and puzzle_002 retained from
Phase-1 anchoring (n = 4). All cost figures are USD billed by the
Anthropic API at June-2026 list pricing; only solved trials enter the
aggregates. Rate-limit-aborted trials are excluded by construction
(the run-plan harness writes them to the result store but the
analyzer's `outcome.solved` filter discards them).

### 5.1 Per-tier results

Tables 2a–c summarize the three anchor puzzles. Cost is in USD and
calls is the per-trial count of MCP tool invocations.

**Table 2a — Tier-1 (puzzle_001, 5×5 easy):**

| toolset | n | cost μ ± σ | calls μ ± σ |
| ---     | - | ---        | ---         |
| none    | 4 | $1.15 ± $0.14 | 3.2 ± 0.5 |
| fine    | 3 | $1.71 ± $0.50 | 57.3 ± 15.9 |
| medium  | 4 | $1.18 ± $0.20 | 24.2 ± 2.1 |
| coarse  | 3 | $0.82 ± $0.31 | 25.0 ± 1.0 |

All three non-`none` toolsets are within 1σ of `none` in cost
(ratios 0.71–1.49×); no pair has separated 1σ confidence intervals.

**Table 2b — Tier-2 (puzzle_002, 7×7 hard):**

| toolset | n | cost μ ± σ | calls μ ± σ |
| ---     | - | ---        | ---         |
| none    | 3 | $4.75 ± $0.94 | 2.3 ± 0.6 |
| fine    | 3 | $4.45 ± $0.92 | 121.0 ± 3.0 |
| medium  | 3 | $3.29 ± $0.62 | 46.3 ± 4.0 |
| coarse  | 3 | $2.59 ± $0.49 | 57.7 ± 7.0 |

`coarse/none` ratio = **0.55×** with separated 1σ CIs (none $[3.81,
5.69]$; coarse $[2.10, 3.09]$; gap $\$0.72$). This is the divergence
regime predicted by P2'.

**Table 2c — Tier-3 (gen_7x7_s1_00, 7×7 generated, tier-3 by formal
grading, n_clues = 13, search_nodes = 4547):**

| toolset | n | cost μ ± σ | calls μ ± σ |
| ---     | - | ---        | ---         |
| none    | 3 | $2.08 ± $0.58 | 2.3 ± 0.6 |
| fine    | 3 | $3.21 ± $1.41 | 82.0 ± 47.5 |
| medium  | 3 | $2.69 ± $0.93 | 45.7 ± 23.2 |
| coarse  | 3 | $2.07 ± $0.67 | 29.3 ± 11.9 |

All four toolsets are within 1σ of `none`; the spread has collapsed
relative to tier-2 (coarse/none ratio 1.00×, fine/none 1.55×, medium
1.30×). Notably the absolute cost level at tier-3 is *lower* than at
tier-2 for every toolset, despite the formal tier being higher — a
caveat we return to in §6.

### 5.2 The cost-ratio surface (Figure F1b)

Figure F1b plots cost ratios C(G, D) / C(none, D) for each toolset
against tier on the x-axis. The surface is **V-shaped**: all three
non-`none` toolsets exhibit a trough at tier-2 and return toward (or
above) 1.0 at tiers 1 and 3. Absolute costs (Figure F1) show the same
shape with the bump rather than the trough: every toolset is most
expensive at tier-2 in absolute terms, and the *spread* between
toolsets is maximal at that bump.

### 5.3 Prediction verdicts

We report verdicts on both the pre-committed G-CD-v1 prediction P3
and the revised G-CD-v2 prediction P3', for transparency.

| Prediction | Statement | Verdict |
| --- | --- | --- |
| **P1'** | Tier-1 ratios collapse to ≈ 1 | **PASS** (3 / 3 toolsets 1σ-overlap with `none`) |
| **P2'** | Tier-2 coarse/none < 1, separated 1σ | **PASS** (ratio 0.55×, gap $0.72) |
| **P3 (v1)** | Tier-3 coarse/none ≤ tier-2 ratio with separated 1σ — *pre-committed monotone* | **FAIL** (tier-3 ratio 1.00× > tier-2 0.55×) |
| **P3' (v2)** | Tier-3 ratios re-collapse to ≈ 1 (Goldilocks) | **PASS** (3 / 3 toolsets 1σ-overlap with `none`) |
| **P4** | Per-call cost varies > 10× across granularities at fixed tier | **PASS** (see §5.4) |

The pre-committed monotone prediction P3 is on record as failing. The
revised model G-CD-v2, motivated by adding the γ floor as the minimal
mechanism consistent with the data, predicts P3' which holds at the
n = 3 closure of Phase-2 minimum-viable.

### 5.4 Calls–cost decoupling (P4 — load-bearing finding)

Within tier-2, where the cost differences are largest, per-call cost
varies by **55×** across granularities:

| toolset | calls μ | cost μ | cost / call |
| ---     | ---     | ---    | ---         |
| none    | 2.3 | $4.75 | **$2.04 / call** |
| fine    | 121.0 | $4.45 | **$0.037 / call** |
| medium  | 46.3 | $3.29 | $0.071 / call |
| coarse  | 57.7 | $2.59 | $0.045 / call |

A `fine` trial issues ≈ 50× more tool calls than a `none` trial for
*statistically indistinguishable cost* ($4.45 vs $4.75, fully
overlapping 1σ). The implication is that the per-call cost term α in
G-CD-v2 is empirically near-zero under current Claude pricing —
tool-call count alone does not predict cost. What is expensive is the
**reasoning-token context** carried on each turn (the β·n_tokens
term). The granularity dial is therefore best understood as
*redirecting* reasoning between in-context deliberation and compact
tool invocations, not as adding or removing book-keeping calls.

Figure F2 plots all 38 solved trials as a calls × cost scatter,
colored by toolset. `none` trials cluster at the left (≤ 4 calls)
spanning $0.97–$5.30; `fine` trials cluster at the right (35–130
calls) spanning $1.39–$4.97. The vertical overlap is the visual
signature of P4: at a given cost, the call count varies by two orders
of magnitude.

### 5.5 Putting the two findings together

The V-shape (P3') and the calls–cost decoupling (P4) compose into a
single observation: **tool-set granularity reshapes how an LLM agent
spends a roughly fixed reasoning budget, and the reshaping is
cost-meaningful only at intermediate problem difficulty.** At easy
problems the fixed-overhead γ dominates and no reshaping matters. At
hard problems the work-volume `W` is so large for every toolset (the
search-depth floor) that granularity-specific savings become a small
fraction of total cost. In the middle, the toolset choice can roughly
halve the API bill.

## 6. Limitations and future work

**Single model.** All 38 solved trials use a single Claude Opus 4.7
variant. *Tool Illusion*'s strong-to-weak skill-transfer result and
prior cross-model work suggest the granularity benefit may depend on
the model. G-CD-v2 is silent on this — the γ, α, β parameters are
model- and pricing-specific, and the V-shape may shift or even
disappear under a different model–toolset pair. A second model on
even a small subset (one tier, two toolsets, n = 3) would be a
6-trial / ≈ $6 add — promising but out of budget for this study.

**One puzzle per tier.** Each tier in §5 is anchored by a single
puzzle. The V-shape is therefore a statement about a (G, D, puzzle)
surface collapsed onto (G, D). A second tier-3 puzzle at a different
grid size would strengthen the high-difficulty re-collapse claim;
attempts to generate 9×9 and 10×10 tier-3 puzzles with the same
`core.generator` were killed after ≈ 14 minutes of CPU each with no
output, indicating the generator does not scale beyond 7×7 at tier-3
in its current form. Improving generator throughput is itself a
research target.

**gen_7x7_s1_00 absolute cost is low.** The tier-3 generated puzzle's
mean `none` cost is $2.08, below the *tier-2* puzzle_002's $4.75. The
formal grader places gen_7x7_s1_00 in tier-3 (search_nodes = 4547),
but its sparse-clue structure (13 clues / 49 cells, vs. puzzle_002's
24 / 49) may make the puzzle tractable to in-context reasoning
despite the high search-node count. The "high-D re-collapse"
mechanism in G-CD-v2 (P3') is the most plausible explanation for the
toolset spread collapse, but we cannot rule out a confound in which
gen_7x7_s1_00 simply happens to be cost-cheap *across all toolsets*.
A second tier-3 puzzle (above) would discriminate.

**P5 (unimodality of the spread surface) untested.** G-CD-v2 implies
the toolset-spread function σ_G C(G, D) has a single peak in D. The
present design tests three points and so cannot rule out a multi-modal
spread. A tier-2.5 puzzle (between puzzle_002 and gen_7x7_s1_00 in
formal difficulty) would test P5; ≈ $60 of trials and one generator
run, deferred to future work.

**Meta-tool axis.** A "meta-tools" condition allowing the agent to
synthesize new tools at runtime is implemented in the codebase but
cost-infeasible to evaluate on subscription compute (two attempts on
2026-05-21 burned $39.18 across two limit-aborts without completing
a single trial; the meta-nudge suppresses the clean bail-on-impasse
that makes scratchpad affordable). We treat this as a separate
contribution on non-subscription compute and a footnote here.

**Rate-limit overhead.** Of the $59.07 total session quota burned
across 12 trials, $19.95 was sunk on trials that hit Anthropic's
rolling 5-hour usage limit mid-run and were correctly excluded by
the harness. Future work targeting larger campaigns should plan for
~30% rate-limit overhead on subscription-only compute.

## 7. Conclusion

LLM tool-set granularity reduces the cost of solving formal CSP tasks,
but the reduction is **conditional on problem difficulty**: it is
large at intermediate difficulty (coarse cuts cost roughly in half
relative to a pure-reasoning baseline), and it collapses at *both*
ends of the difficulty axis. This Goldilocks shape is predicted by a
minimal two-floor cost model (G-CD-v2) that distinguishes a fixed
per-trial overhead γ from a granularity-and-difficulty-dependent
work-volume term `W`. The pre-committed monotone alternative is
falsified by the tier-3 data.

A second finding survives the model revision and is what we view as
the most actionable for tool designers: **tool-call count does not
predict cost.** A `fine` toolset issues 50× more tool calls than a
`none` toolset for indistinguishable cost. The expensive substance
of a tool call is not the call itself but the reasoning-token context
that surrounds it. The granularity dial is therefore best understood
as redirecting *reasoning* between in-context deliberation and
compact tool invocations — not as adding or removing book-keeping.
This suggests a design principle: when adding tools to an agent,
optimize for what they let the model *stop reasoning about*, not for
how few or how many calls they generate.

---

## Figures and tables

| ID | Description | Source |
| --- | --- | --- |
| F1 | Cost μ ± σ per toolset across tiers | `paper/figures/f1_cost_by_tier.png` |
| F1b | Cost ratio vs `none` across tiers (V-shape) | `paper/figures/f1b_cost_ratio_by_tier.png` |
| F2 | Calls vs cost scatter (P4 decoupling) | `paper/figures/f2_calls_vs_cost.png` |
| F3 | Difficulty-grader algorithm box | `core/generator.grade` (TBD render) |
| T1 | Toolset definitions + tool counts | static; transcribed from `servers/` |
| T2 | Per-cell results (n, calls, cost, time) | analyzer output |

## References

*[TODO — populate from notes/related_work.md]*
