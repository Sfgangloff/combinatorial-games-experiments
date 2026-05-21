"""
Procedural Slitherlink generator + solution counter + difficulty grader.

Why this exists (notes/2026-05-18_aaai_plan_and_meta_confound.md): a
main-track paper on public puzzle-loop.com instances is rejectable on
training-contamination grounds. This module produces *seeded,
contamination-free* instances with a *formal difficulty tier* — the axis
that differentiates us from The Tool Illusion. The solution counter here
is also the project's first committed uniqueness verifier (the manifest
claims uniqueness but no checker was ever committed — a reproducibility
gap a reviewer would flag).

Construction: the solution loop is the boundary of a random
simply-connected set of cells R. The boundary of any simply-connected
polyomino is exactly one simple closed loop, so every generated solution
is valid by construction. Clues = per-cell count of boundary edges. We
then drop clues greedily while `count_solutions(..., limit=2) == 1`, so
the published puzzle has a unique solution that is verified, not assumed.

Difficulty tier:
  1  pure local propagation solves it
  2  propagation + 1-ply lookahead to fixpoint solves it (the coarse
     engine's reach)
  3+ requires real backtracking search; `search_nodes` is the finer
     continuous hardness proxy

CLI:
    python -m core.generator --selftest
    python -m core.generator --rows 7 --cols 7 --seed 42 --count 3 \
        --min-tier 2 --out-dir puzzles --emit-manifest
"""
from __future__ import annotations

import argparse
import json
import random
from collections import deque
from pathlib import Path

from core.analysis import is_solved
from core.parser import load_from_text
from core.propagation import propagate
from core.render import render
from core.state import EdgeState, SlitherlinkState

GENERATOR_VERSION = 1


# --------------------------------------------------------------------------
# Region generation (simply-connected polyomino -> guaranteed single loop)
# --------------------------------------------------------------------------

def _no_holes(region: set[tuple[int, int]], rows: int, cols: int) -> bool:
    """
    True iff every non-region cell is reachable from outside the grid
    through non-region cells — i.e. R is simply connected (its boundary
    is one simple closed loop, not a loop-plus-hole).
    """
    non_region = {
        (r, c)
        for r in range(rows)
        for c in range(cols)
        if (r, c) not in region
    }
    if not non_region:
        return True  # R == whole grid; boundary is the grid border (valid)
    border = deque(
        (r, c) for (r, c) in non_region
        if r in (0, rows - 1) or c in (0, cols - 1)
    )
    if not border:
        return False  # non-region cells exist but none touch the border
    seen = set(border)
    while border:
        r, c = border.popleft()
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nr, nc = r + dr, c + dc
            if (nr, nc) in non_region and (nr, nc) not in seen:
                seen.add((nr, nc))
                border.append((nr, nc))
    return len(seen) == len(non_region)


def random_region(
    rows: int, cols: int, rng: random.Random
) -> set[tuple[int, int]]:
    """Grow a random connected, hole-free region of ~30–70% of the grid."""
    total = rows * cols
    target = rng.randint(max(1, total // 3), max(1, (2 * total) // 3))
    seed = (rng.randrange(rows), rng.randrange(cols))
    region = {seed}
    frontier = {seed}
    while len(region) < target:
        candidates: set[tuple[int, int]] = set()
        for (r, c) in frontier:
            for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nr, nc = r + dr, c + dc
                if 0 <= nr < rows and 0 <= nc < cols and (nr, nc) not in region:
                    candidates.add((nr, nc))
        if not candidates:
            break
        order = list(candidates)
        rng.shuffle(order)
        added = False
        for cell in order:
            region.add(cell)
            if _no_holes(region, rows, cols):
                frontier = region
                added = True
                break
            region.discard(cell)
        if not added:
            break
    return region


# --------------------------------------------------------------------------
# Region -> solution loop + clues
# --------------------------------------------------------------------------

def _in_region(region: set[tuple[int, int]], r: int, c: int,
               rows: int, cols: int) -> bool:
    return 0 <= r < rows and 0 <= c < cols and (r, c) in region


def solution_state(region: set[tuple[int, int]], rows: int,
                    cols: int) -> SlitherlinkState:
    """The fully-solved state whose LINE edges are the boundary of R."""
    st = SlitherlinkState.empty(rows, cols)
    for dr in range(rows + 1):
        for c in range(cols):
            on = _in_region(region, dr, c, rows, cols) != \
                _in_region(region, dr - 1, c, rows, cols)
            st.h_edges[(dr, c)] = EdgeState.LINE if on else EdgeState.BLOCKED
    for cr in range(rows):
        for dc in range(cols + 1):
            on = _in_region(region, cr, dc, rows, cols) != \
                _in_region(region, cr, dc - 1, rows, cols)
            st.v_edges[(cr, dc)] = EdgeState.LINE if on else EdgeState.BLOCKED
    return st


def full_clues(sol: SlitherlinkState) -> dict[tuple[int, int], int]:
    return {
        (r, c): sol.count_edges_around_cell(r, c)[EdgeState.LINE]
        for r in range(sol.num_rows)
        for c in range(sol.num_cols)
    }


def _puzzle_state(rows: int, cols: int,
                  clues: dict[tuple[int, int], int]) -> SlitherlinkState:
    return SlitherlinkState.empty(rows, cols, clues)


# --------------------------------------------------------------------------
# Solution counter (also the uniqueness verifier) + difficulty grader
# --------------------------------------------------------------------------

def _closed_component_exists(state: SlitherlinkState) -> bool:
    """A LINE component with no degree-1 dot: it can no longer grow."""
    from core.analysis import endpoints, line_components
    comps = line_components(state)
    if not comps:
        return False
    eps = set(endpoints(state))
    return any(eps.isdisjoint(comp) for comp in comps)


def _pick_unknown(state: SlitherlinkState) -> tuple[str, int, int] | None:
    """Most-constrained branch edge: extend an open path end if possible."""
    from core.analysis import endpoints
    for (dr, dc) in endpoints(state):
        for et, r, c in state.edges_at_dot(dr, dc):
            if state.get_edge(et, r, c) == EdgeState.UNKNOWN:
                return (et, r, c)
    for (r, c) in state.h_edges:
        if state.h_edges[(r, c)] == EdgeState.UNKNOWN:
            return ("H", r, c)
    for (r, c) in state.v_edges:
        if state.v_edges[(r, c)] == EdgeState.UNKNOWN:
            return ("V", r, c)
    return None


def count_solutions(state: SlitherlinkState, limit: int = 2) -> dict:
    """
    Count valid full solutions up to `limit`. Returns
    {'count': int, 'nodes': int}. count==1 over the whole grid means the
    puzzle's solution is unique (this is the uniqueness verifier).
    """
    nodes = 0

    def rec(st: SlitherlinkState) -> int:
        nonlocal nodes
        nodes += 1
        work = st.clone()
        if propagate(work).contradiction is not None:
            return 0
        if _closed_component_exists(work):
            return 1 if is_solved(work)[0] else 0
        nxt = _pick_unknown(work)
        if nxt is None:
            return 1 if is_solved(work)[0] else 0
        et, r, c = nxt
        found = 0
        for val in (EdgeState.LINE, EdgeState.BLOCKED):
            branch = work.clone()
            branch.set_edge(et, r, c, val)
            found += rec(branch)
            if found >= limit:
                return found
        return found

    count = rec(state)
    return {"count": min(count, limit), "nodes": nodes}


def _solved_by_propagation(state: SlitherlinkState) -> bool:
    work = state.clone()
    if propagate(work).contradiction is not None:
        return False
    return is_solved(work)[0]


def _solved_by_lookahead(state: SlitherlinkState,
                         max_rounds: int = 500) -> bool:
    work = state.clone()
    for _ in range(max_rounds):
        if propagate(work).contradiction is not None:
            return False
        if is_solved(work)[0]:
            return True
        progressed = False
        for et, r, c in work.all_edges():
            if work.get_edge(et, r, c) != EdgeState.UNKNOWN:
                continue
            forced: EdgeState | None = None
            for val, opp in ((EdgeState.LINE, EdgeState.BLOCKED),
                             (EdgeState.BLOCKED, EdgeState.LINE)):
                trial = work.clone()
                trial.set_edge(et, r, c, val)
                if propagate(trial).contradiction is not None:
                    forced = opp
                    break
            if forced is not None:
                work.set_edge(et, r, c, forced)
                progressed = True
        if not progressed:
            return False
    return False


def grade(state: SlitherlinkState) -> dict:
    """{'tier': 1|2|3, 'search_nodes': int} — the formal difficulty axis."""
    if _solved_by_propagation(state):
        tier = 1
    elif _solved_by_lookahead(state):
        tier = 2
    else:
        tier = 3
    nodes = count_solutions(state, limit=2)["nodes"]
    return {"tier": tier, "search_nodes": nodes}


# --------------------------------------------------------------------------
# Clue reduction -> unique minimal puzzle
# --------------------------------------------------------------------------

def reduce_to_unique(rows: int, cols: int,
                     full: dict[tuple[int, int], int],
                     rng: random.Random) -> dict[tuple[int, int], int]:
    """Drop clues in random order while the solution stays unique."""
    clues = dict(full)
    order = list(clues.keys())
    rng.shuffle(order)
    for cell in order:
        trial = dict(clues)
        del trial[cell]
        if count_solutions(_puzzle_state(rows, cols, trial),
                           limit=2)["count"] == 1:
            clues = trial
    return clues


# --------------------------------------------------------------------------
# One puzzle
# --------------------------------------------------------------------------

def generate_one(rows: int, cols: int, rng: random.Random,
                  min_tier: int = 1, max_attempts: int = 60) -> dict | None:
    """Generate one unique puzzle meeting min_tier, or None if it can't."""
    for _ in range(max_attempts):
        region = random_region(rows, cols, rng)
        if not region or len(region) == rows * cols:
            continue
        sol = solution_state(region, rows, cols)
        if count_solutions(_puzzle_state(rows, cols, full_clues(sol)),
                           limit=2)["count"] != 1:
            continue  # ambiguous even with all clues (rare); reroll
        clues = reduce_to_unique(rows, cols, full_clues(sol), rng)
        st = _puzzle_state(rows, cols, clues)
        g = grade(st)
        if g["tier"] < min_tier:
            continue
        text = render(st, show_blocked=False)
        # provenance + round-trip sanity
        assert _clue_dict(load_from_text(text)) == clues, "serialize round-trip"
        return {
            "rows": rows, "cols": cols,
            "num_clues": len(clues),
            "tier": g["tier"], "search_nodes": g["search_nodes"],
            "region_size": len(region),
            "text": text,
        }
    return None


def _clue_dict(st: SlitherlinkState) -> dict[tuple[int, int], int]:
    return dict(st.cells)


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def _selftest() -> None:
    rng = random.Random(12345)
    ok = 0
    for size in (4, 5, 6):
        p = generate_one(size, size, rng, min_tier=1)
        assert p is not None, f"failed to generate {size}x{size}"
        st = load_from_text(p["text"])
        cnt = count_solutions(st, limit=3)
        assert cnt["count"] == 1, f"{size}x{size} not unique: {cnt}"
        assert 1 <= p["tier"] <= 3
        print(f"  {size}x{size}: clues={p['num_clues']} tier={p['tier']} "
              f"nodes={p['search_nodes']} unique=OK")
        ok += 1
    print(f"selftest passed ({ok}/3): generation, uniqueness, round-trip.")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--rows", type=int, default=7)
    ap.add_argument("--cols", type=int, default=7)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--count", type=int, default=1)
    ap.add_argument("--min-tier", type=int, default=1, choices=(1, 2, 3))
    ap.add_argument("--out-dir", default=None,
                    help="write puzzle .txt files here (gen_*.txt)")
    ap.add_argument("--emit-manifest", action="store_true",
                    help="print manifest fragment JSON for generated puzzles")
    a = ap.parse_args()

    if a.selftest:
        _selftest()
        return

    rng = random.Random(a.seed)
    entries = []
    for i in range(a.count):
        p = generate_one(a.rows, a.cols, rng, min_tier=a.min_tier)
        if p is None:
            print(f"# gen {i}: no puzzle met min-tier={a.min_tier}")
            continue
        name = f"gen_{a.rows}x{a.cols}_s{a.seed}_{i:02d}"
        print(f"# {name}: clues={p['num_clues']} tier={p['tier']} "
              f"nodes={p['search_nodes']}")
        print(p["text"])
        if a.out_dir:
            out = Path(a.out_dir) / f"{name}.txt"
            out.write_text(p["text"] + "\n")
        entries.append({
            "id": name,
            "size": f"{a.rows}x{a.cols}",
            "difficulty": f"tier{p['tier']}",
            "source": "procedurally generated (core.generator)",
            "seed": a.seed,
            "generator_version": GENERATOR_VERSION,
            "tier": p["tier"],
            "search_nodes": p["search_nodes"],
            "num_clues": p["num_clues"],
            "file": f"{name}.txt",
        })
    if a.emit_manifest and entries:
        print("\n# manifest fragment:")
        print(json.dumps({"puzzles": entries}, indent=2))


if __name__ == "__main__":
    main()
