# Status checkpoint + AAAI-27 plan + meta-axis confound

**Date:** 2026-05-18. **Status:** planning checkpoint, no new runs.
**Trigger:** publication target changed to **AAAI-27 main technical
track** (was ICML/NeurIPS in `research_plan.md`); compute is
**subscription-only**; user directive is "do everything, slip to
ICML/NeurIPS if we miss the AAAI window."

## Where we are

- **Phase 0 (lit review):** done. Descriptive "granularity matters" is
  scooped (*The Tool Illusion*, COLM 2026, web-agent domain).
  Defensible novelty reframed to: (i) formal-difficulty CSP testbed,
  (ii) model×granularity interaction, (iii) predictive theory.
- **Phase 1 (replication):** **open, leaning negative.** puzzle_001
  (5×5 easy, n=3–4) *killed* the pilot headline — none/medium/coarse
  cost CIs overlap at 1σ; only "fine is reproducibly most expensive"
  survived. The deciding hard-puzzle replication (puzzle_002, 7×7,
  n≥3 × 4 toolsets, meta-off) **was never run**. The Phase-1 → Phase-2
  gate is therefore unresolved.
- **Scratchpad detour (off-gate):** v1 (frame stack) → v2 (`try_both`,
  1-ply engine lookahead). v2 sweep (n=1): solves 5×5 easy + 7×7 hard,
  −19% vs v1 easy, +85% on 7×7 (try_both overused), clean −85% bail on
  15×15 (unsolved). 15×15 hard is the ceiling for all 5 toolsets.
- **Last run crashed:** May 12 meta-nudge run died on `ECONNRESET`,
  unanalyzed.

## Meta-axis confound (correction)

Prior conclusion "meta-tools are inert because the model doesn't need
them" (May-7 baseline note) is **confounded and withdrawn**: the
meta-tools MCP server required a backend API that was **never
configured**, so working meta-tools may never have been in the model's
tool list. The user has since configured it — `claude mcp get
meta-tools` now reports `✓ Connected`. Meta has **never had a fair
test**.

**Scope decision:** meta-tools (agent self-extension) is *orthogonal*
to tool granularity. It is **not** a matrix axis for the AAAI paper
(footnote/appendix only, regardless of outcome); a surprising result
becomes a *separate* paper. Remove the four `meta=True` entries from
`ALL_CONDITIONS` so the main matrix is meta-free.

**Probe update (2026-05-18):** the cheap probe
(`20260518T033633_puzzle_001_...scratchpad_meta-on`) solved cleanly
with **zero meta-tool calls** — but this was a **probe-design error**:
the meta-nudge only fires on the bail pathway, and an easy puzzle is
never bailed on, so the trigger never arises. puzzle_002 is also
solved by scratchpad ⇒ won't bail either. The **only fair, affordable
meta test is `puzzle_004 scratchpad meta-on`** (~$3–4 via v2
clean-bail). Sequencing (firm): run it as ONE isolated run *after* the
Phase-1 gate closes — not folded into a Phase-1 window, because the
budget cap is pre-run only and a meta-on puzzle_004 run is
cost-unpredictable (the nudge suppresses clean bail). Gate is
priority #1.

## Timeline arithmetic (subscription-only is the binding constraint)

- 1 window ≈ $8–10, sequential, frequently truncated; ~1–2 usable
  windows/day with babysitting.
- Phase-1 close ≈ ~$32 ≈ 3–4 windows ≈ ~3–5 days.
- Phase 2 (~144 runs, ~$290) ≈ ~30 windows ≈ **3–5 weeks** disciplined.
- Phase 3 same order; Phases 4–5 more.
- ⇒ "everything" on subscription-only = 3–4+ months = ICML/NeurIPS
  pace. The only AAAI-27-main-track-shaped scoped unit is **Phase-1
  gate closed + Phase-2 difficulty-frontier, single model,
  contamination-controlled**. Everything else is the accepted slip.

## Next steps, ordered by information-per-window

1. **Close the Phase-1 gate (priority #1, compute).** puzzle_002 ×
   {none, fine, medium, coarse} × n≥3, meta-off. Decision rule
   (pre-committed): coarse/none cost ratio on the *hard* puzzle with
   non-overlapping 1σ CIs ⇒ descriptive frontier is real ⇒ Phase 2
   justified. Collapses to overlap (as the easy puzzle did) ⇒
   descriptive kernel dead ⇒ pivot the paper to the
   theory/interaction angle. **No Phase-2 budget before this resolves.**
2. **Fair meta test = `puzzle_004 scratchpad meta-on`, ONE isolated
   run AFTER the gate closes** (not folded into a Phase-1 window — see
   probe update above). Then drop the meta axis and write it up.
3. **DONE — `core/generator.py`.** Seeded procedural generation,
   committed solution-counter / uniqueness verifier (no backtracker
   existed in-repo — the manifest's uniqueness claims were unverified),
   formal tier grader (1=propagation, 2=+1-ply, 3+=search +
   search_nodes). Selftest passes 4×4/5×5/6×6 unique + round-trip.
4. **DONE — `harness/run_plan.py`.** Resumable, window-budget-capped,
   rate-limit-abort-safe batch runner with `--dry-run`. Window 1
   (2026-05-18) ran clean: meta probe + puzzle_002 coarse + medium,
   $7.60, stopped before fine, 4 trials left.

Critical path now: resume Phase-1 windows (none×2, fine×2) → gate
verdict → branch (Phase-2 difficulty buckets via the generator, or
pivot to theory/interaction if the ratios collapse like the easy
puzzle).

## Window log

- **W1 2026-05-18** ($7.60, 80.6 min): puzzle_001 scratchpad meta-on
  solved $0.75 (0 meta calls — invalid nudge test, see above);
  puzzle_002 coarse meta-off solved 57 calls $3.16;
  puzzle_002 medium meta-off solved 44 calls $3.68. puzzle_002 good
  trials now: none=1, fine=1, medium=3, coarse=3 (need none+2, fine+2).
- **W2 2026-05-18** ($3.45, 19 min): one puzzle_002 fine meta-off trial
  hit the usage limit mid-run (~70 calls, not solved). Correctly NOT
  counted; runner stopped clean. Exposed that the real rate-limit error
  is a generic "Command failed with exit code 1 / Fatal error in
  message reader" — not the keywords the abort-guard checked. Hardened
  `harness/run_plan._classify`: ANY record-level error now → abort the
  batch (resume is idempotent so stopping is always safe).
- **W3 2026-05-18** (loop iter 1, $4.98, 17 min): limit had cleared.
  puzzle_002 fine meta-off solved, 121 calls. fine now n=2. Self-paced
  /loop active, auto-continuing remaining windows.
- **W4 2026-05-18→20** (loop iter 2, $6.91, 59 min, NOT counted): tried
  next fine trial; hit the usage limit mid-run. Hardened classifier
  correctly aborted with the new message. The $6.91 of subscription
  quota is sunk cost of running on subscription-only when the limit
  hits mid-trial. State unchanged.
- **W5 2026-05-20** (loop iter 3, $4.06, 23 min, NOT counted): same
  pattern — fine trial hit limit mid-run. Cumulative wasted quota on
  limit-mid-run hits: $3.45 + $6.91 + $4.06 ≈ **$14.4** (≈3 successful
  fine trials' worth) for zero counted progress. Lesson: a ~30-min
  retry fallback catches a still-depleted rolling 5h window. Loop now
  stretches fallback to the ScheduleWakeup max (3600s = 1h) after a
  limit-hit; two consecutive max-sleeps ≈ 2h gap before next attempt.
- **W6 2026-05-21** ($5.31, 32 min): puzzle_002 none meta-off solved
  in 3 tool calls (1 get_puzzle + 2 submit, one rejected → corrected).
  Runner stopped cleanly on window-budget threshold ($5.31 + ~$5.28 >
  $8). none n=2.
- **W7 2026-05-21** ($3.67, 22 min): final puzzle_002 none meta-off
  solved in 2 calls. **Gate closed: all four toolsets at n=3.**
  (Fine had already reached n=3 at some earlier point between the note
  draft and the W6 dry-run — the note's `fine=2` was stale.)
- **W8 2026-05-21** ($6.17, 18.5 min, NOT counted): first attempt at
  the fair meta test (`puzzle_004 scratchpad meta-on`). Hit the rolling
  5h usage limit mid-trial; hardened classifier aborted cleanly. Note:
  $6.17 burned in 18.5 min suggests the real cost of a *completed*
  meta-on scratchpad trial on puzzle_004 may be well above the $3–4
  estimate (the meta-nudge plausibly suppresses the clean bail).
- **W9 2026-05-21** ($18.61, 24.5 min, NOT counted): retry of the same
  meta probe. Hit the limit again at a much higher burn — $18.61 in
  24.5 min before abort. Confirms the meta-nudge breaks the v2
  clean-bail design: a completed trial would likely cost $25–40+. The
  $3–4 prediction was wrong because it was based on bail-pathway
  behavior the nudge explicitly suppresses.

## Meta axis: dropped (2026-05-21)

The "one isolated fair test" plan is **dead** on subscription compute.
Two attempts, $39.18 ($6.17 + $18.61 + $14.4 prior fine aborts) wasted,
no completed meta-on trial. The only puzzle where scratchpad's clean
bail makes meta affordable is also the only puzzle where the
meta-nudge prevents the clean bail. There is no fair, cost-bounded
test cell on subscription compute.

**Decision (firm):** drop the meta axis from the AAAI matrix entirely.
Paper write-up = footnote/appendix only: two paragraphs on the design
+ the empirical finding that on subscription compute the test cell is
cost-unbounded. A surprising positive result becomes a separate paper
with non-subscription compute. Memory file
`meta-axis-dropped-cost-infeasible.md` supersedes
`meta-axis-inert-may12-untested.md`.

**Code follow-up (non-blocking):** remove or flag-gate the four
`meta=True` entries in `harness/conditions.py:101-107` so they can't
be folded back into Phase 2 by accident.

## Phase-1 gate verdict (2026-05-21): PASS

`puzzle_002` (7×7 hard, meta-off, n=3 each, solved trials only):

| toolset    | n | tool calls   | wall min    | cost USD    |
| ---        | - | ---          | ---         | ---         |
| none       | 3 | 2.33 ± 0.58  | 27.8 ± 5.6  | **4.75 ± 0.94** |
| fine       | 3 | 121.0 ± 3.0  | 17.2 ± 4.2  | 4.45 ± 0.92 |
| medium     | 3 | 46.3 ± 4.0   | 28.7 ± 28.5 | 3.29 ± 0.62 |
| coarse     | 3 | 57.7 ± 7.0   | 11.8 ± 3.2  | **2.59 ± 0.49** |
| scratchpad | 2 | 50.0 ± 18.4  | 12.2 ± 1.8  | 3.67 ± 1.54 |

Pre-committed decision rule (from this note's "Next steps" §1):
non-overlapping 1σ CIs on coarse/none cost ⇒ descriptive frontier real
⇒ Phase 2 justified.

- coarse/none cost ratio = **0.55×** (coarse half the cost of none)
- 1σ CIs: none **[3.81, 5.69]**, coarse **[2.10, 3.09]** — **$0.72 gap**
- ⇒ **gate PASS. Phase 2 budget unlocked.**

**Findings worth carrying forward:**
- `none` solves the hard puzzle in 2–3 tool calls (model holds the
  whole 7×7 in context) but is the *most expensive* toolset by cost —
  in-context reasoning is real work.
- `fine` is uniquely expensive in *tool calls* (121) but cost is
  comparable to `none` — primitive bookkeeping doesn't burn many
  tokens per call.
- `coarse` 1.8× cheaper and 2.4× faster than `none`. Suggested-move
  + propagation removes both reasoning depth and wall time.
- This is the inverted-shape of puzzle_001 (easy), where cost CIs
  collapsed to overlap. Difficulty matters — the granularity signal
  is conditional on hard-enough puzzles, which is itself a useful
  paper finding.

## RESUME HERE (Phase-1 gate is closed)

Critical path (in order):

1. ~~**Fair meta test**~~ — **dropped 2026-05-21** (cost infeasible,
   see "Meta axis: dropped" above). Footnote/appendix only.
2. **Phase 2 plan**: difficulty-frontier sweep, single model,
   contamination-controlled, generated via `core.generator` so
   puzzles are seed-locked and uniqueness-verified. Design the
   difficulty buckets (tier-1 propagation-only, tier-2 +1-ply,
   tier-3+ search-required) × 4 toolsets × n=3. ~144 runs as
   originally scoped, ~$290, ~30 windows ≈ 3–5 weeks disciplined.
3. Commit the uncommitted scaffolding (`core/generator.py`,
   `harness/run_plan.py`, the README rewrite, this note) before
   Phase 2 starts so any later result hashes to a clean tree.
