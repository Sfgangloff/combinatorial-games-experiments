# slitherlink-scratchpad — toolset design (proposal)

**Date:** 2026-05-09. **Status:** design proposal, not yet implemented.
**Goal:** test whether *automated branch-state bookkeeping* lets the model
solve harder Slitherlinks than the current `medium` toolset, at lower
token cost.

## Motivation (recap)

On puzzle_004 (15×15 hard), `medium` made 162 calls (71 `apply_edge`,
30 `forced_moves`, 11 `snapshot`, 9 `restore`) and cost $29.93 — 7×
fine, 9× coarse. It did not solve. The model's closing line was
"kept hitting contradictions in case-splits."

Hypothesis: the cost and the failure both come from the same place
— the model has the deductive primitives but cannot reliably manage
**which assumption it is currently testing**, **what depth in the
search tree it is at**, and **what state to restore to** when a branch
fails. Each `snapshot`/`restore` pair shifts that bookkeeping into
assistant-level reasoning tokens, paid at the highest billing rate.

A scratchpad toolset moves the bookkeeping into the engine. The model
declares hypotheses; the engine maintains the stack and auto-retracts
on contradiction.

## Tool surface (proposed)

Server name: **`slitherlink-scratchpad`**, parallel to fine / medium /
coarse. Adds a 5th condition `toolset=scratchpad` to the matrix
without touching the other servers.

The toolset is a **superset of medium's local-deduction primitives**
(load, render, apply_edge, forced_moves, check_consistency, endpoints,
solved) **plus a frame stack** that replaces snapshot/restore.

### Frame primitives (the new part)

| Tool                 | Args                                  | Returns                                      |
|----------------------|---------------------------------------|----------------------------------------------|
| `assume`             | handle, rationale: str, edges: list[{type, row, col, value}] | frame_id, depth, summary, contradiction_after_propagation |
| `commit`             | handle, frame_id (must be top)        | frame's edges become facts at parent level   |
| `retract`            | handle, frame_id (must be top)        | pop frame; state restored to parent          |
| `frames`             | handle                                | list of {frame_id, depth, rationale, parent_id, edges_added, status} |
| `current_frame`      | handle                                | the top frame plus its full ancestry         |

**Semantics.**

- The engine maintains an internal stack of `SlitherlinkState`
  snapshots (one per frame).
- `assume` clones the top state, applies the given edges with full
  local propagation, pushes the result onto the stack as a new frame.
  The model writes a *rationale* string (e.g. "test that edge (3,5)
  is on so row-3 cluster of 2s closes downward").
- If propagation hits a contradiction, the engine **does not
  auto-retract** — it returns `contradiction_after_propagation: <reason>`
  and leaves the frame open. The model decides whether to retract
  (the assumption was wrong → its negation is now a fact at the
  parent level) or to inspect further. Auto-retract is tempting but
  removes the model's chance to learn from the contradiction; we want
  the **info** auto-derived (it's wrong), not the **action**.
- `commit` is only valid when the top frame has no contradiction. It
  collapses the frame's edges into the parent state.
- `retract` is always valid; it discards the top frame.
- After a `retract` of frame F where F detected a contradiction, the
  parent state may be updated with the **negation** of the assumption
  — i.e., if the model assumed edge X = LINE and it contradicted, then
  X = BLOCKED is now a fact. **The engine offers this** as part of the
  retract response (`negation_applied: {...}`), but does not force it
  — model can decline if it doesn't trust the contradiction.

**Depth limit.** Hard cap at 5 nested frames. If the model tries to
`assume` at depth 5, the call returns an error suggesting it commit or
retract first. This prevents the runaway nesting that caused medium's
$29.93.

**Frame-level deductions.** All medium-tier tools (`apply_edge`,
`forced_moves`, `check_consistency`, `endpoints`, `render`, `solved`)
operate on the **top frame** (or the root state if no frame is open).
The model never has to address a specific frame — the stack is
implicit "current context."

### Inherited primitives (unchanged from medium)

| Tool                 | Behavior                                          |
|----------------------|---------------------------------------------------|
| `load`               | parse puzzle, return handle + summary             |
| `render`             | ASCII view of current frame                       |
| `apply_edge`         | set one edge in current frame, propagate          |
| `forced_moves`       | preview forced edges in current frame             |
| `check_consistency`  | detect violations in current frame                |
| `endpoints`          | dots with exactly 1 line edge in current frame    |
| `solved`             | whether current frame is a complete solution      |

Notably **removed from medium**: `snapshot`, `restore`. The frame
stack subsumes them.

## What the model's loop looks like

```
1. apply_edge(...) until forced_moves() is empty.
2. inspect endpoints + check_consistency to pick a candidate
   case-split.
3. assume(rationale="testing edge X line", edges=[X line]).
4. apply_edge(...) and forced_moves() inside the frame.
5a. If contradiction:
       retract(frame). Engine offers negation; model accepts or
       declines. State now has X blocked at parent level (free
       deduction).
5b. If solved at frame level:
       commit(frame).
5c. If stuck but no contradiction:
       (depth < 5) assume(...) for a sub-hypothesis, or
       retract(frame) and try a different split.
6. Loop.
```

The expensive thing in medium — "what was I assuming, where am I in
the tree, what should I restore to" — is now `current_frame()`, one
cheap tool call.

## Why this might work

1. **Branch state is engine-managed, not in tokens.** The model
   doesn't carry "I'm in branch B which is under branch A" in its
   working memory. It calls `current_frame` when it needs to know.
2. **Negation extraction is free.** Today the model has to *notice*
   that a failed assumption gives free information, then *manually*
   apply the negated edge. The engine offers it, so this deduction
   stops being a thinking step.
3. **Depth cap prevents flailing.** The medium runs likely got
   stuck nesting hypotheses. Capping at 5 forces the model to either
   resolve current branches or backtrack — no infinite descent.
4. **Rationale strings are self-documenting context.** When the
   model calls `frames`, it sees its own reasoning chain. This is
   cheaper than re-deriving "why did I assume this" from scratch.

## Why this might NOT work (failure modes to watch)

- **The model still has to choose what to assume.** The hard part of
  search is splitting on the right variable. Scratchpad doesn't help
  with this. If the model splits randomly, depth-5 won't be enough.
- **Rationale strings could be padding.** If the model writes terse
  or hallucinated rationales, the docs become noise.
- **Contradictions that are not local.** `propagation` only catches
  local violations. Loop-shape violations (multi-component, premature
  closure, parity) need analysis the engine may not do at frame time
  — so a frame might "succeed" propagation but be globally
  inconsistent. The model would commit garbage.
  → Mitigation: run `check_consistency` (which already detects
  multi-component / premature closure) at every `assume` and report
  in the response.

## Implementation sketch

- `servers/slitherlink-scratchpad/server.py`, ~250 lines, mirrors
  `slitherlink-medium/server.py` structure.
- Replace `_snapshots: dict[str, dict[str, SlitherlinkState]]` with
  `_frame_stacks: dict[str, list[Frame]]`, where `Frame` is a small
  dataclass: `{id, parent_id, rationale, state, status,
  edges_added}`.
- Reuse `core.apply_edge`, `core.forced_moves`,
  `core.check_consistency`, `core.is_solved`, `state.clone()`.
- Register in `harness/conditions.py` as a new toolset literal:
  `Toolset = Literal["none", "fine", "medium", "coarse", "scratchpad"]`,
  add to `ALL_CONDITIONS` (or leave out of the default matrix and
  only run via `run_subset.py` for now).

## Evaluation plan

Before declaring win/loss:

1. **Sanity:** scratchpad solves puzzle_001 (5×5 easy). If it can't,
   something is broken.
2. **Comparison vs medium on puzzle_002 (7×7 hard, n=3 each).**
   - Did either solve? (Both failure or both success is informative.)
   - Cost: scratchpad expected to be ≤ medium. If higher, hypothesis
     refuted.
   - Tool-call mix: did the model actually use frames, or did it just
     apply edges and never branch?
3. **If puzzle_002 looks promising: try puzzle_004 (15×15 hard, n=1).**
   - Did it solve? If yes, this is a real result regardless of cost.
   - If no, did it submit at all? (Medium didn't.) A submit attempt
     is itself progress.
4. **Track frame depth distribution.** If the model never goes
   deeper than 1, the scratchpad wasn't doing anything different
   from sequential apply_edge.

## Open questions (for discussion before code)

1. Should `assume` accept multiple edges in one call, or one at a
   time? Multi-edge is more efficient but conflates "a hypothesis"
   with "a sequence of independent edge sets."
2. Should the engine *automatically* run `forced_moves` to fixpoint
   inside a frame on `assume`, or only `apply_edge`'s built-in
   propagation? Auto-fixpoint is more powerful but hides work.
3. Is the depth cap of 5 right? Could be a parameter; default 5.
4. Should we add `try_both`(edge) — engine assumes edge=line, runs
   propagation, retracts; assumes edge=blocked, runs propagation,
   retracts; reports which (if any) survives? This is "1-ply
   lookahead at one edge," already in coarse — but exposing it
   inside scratchpad would make case-splits cheaper still. Risk: it
   blurs the line between scratchpad and coarse.

## What we will *not* do

- No SAT/CSP solver inside the engine. The point is to test whether
  the model can do search if bookkeeping is offloaded — not to
  delegate solving.
- No global loop-shape inference beyond what
  `core.check_consistency` already does.
- No conflict-driven clause learning (CDCL). That's research-grade
  scope creep.
