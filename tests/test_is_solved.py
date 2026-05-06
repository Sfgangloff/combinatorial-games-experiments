"""
Comprehensive tests for core.is_solved.

Goal: cover every way a Slitherlink state can be valid or invalid, so we trust
is_solved as the experimental ground truth.

Each test builds a state (either via load_from_text or directly via the
SlitherlinkState API), then asserts is_solved's verdict. Negative tests also
check that the failure reason mentions the responsible feature.
"""
from pathlib import Path

from core import EdgeState, SlitherlinkState, is_solved, load_from_text

REPO = Path(__file__).resolve().parent.parent


def _set_h(state: SlitherlinkState, *cells: tuple[int, int]) -> None:
    for r, c in cells:
        state.h_edges[(r, c)] = EdgeState.LINE


def _set_v(state: SlitherlinkState, *cells: tuple[int, int]) -> None:
    for r, c in cells:
        state.v_edges[(r, c)] = EdgeState.LINE


# ---------- POSITIVE CASES ----------

def test_solved_1x1_unit_loop_no_constraints():
    """A 1x1 cell with all 4 sides drawn as LINE forms a closed loop."""
    s = SlitherlinkState.empty(1, 1)
    _set_h(s, (0, 0), (1, 0))
    _set_v(s, (0, 0), (0, 1))
    ok, reason = is_solved(s)
    assert ok, reason


def test_solved_1x1_with_cell_4_not_used():
    """No-number cell + closed loop is fine (no number = no constraint)."""
    s = SlitherlinkState.empty(1, 1)
    _set_h(s, (0, 0), (1, 0))
    _set_v(s, (0, 0), (0, 1))
    ok, reason = is_solved(s)
    assert ok, reason


def test_solved_2x2_outer_perimeter_no_numbers():
    """Loop runs around the outside of a 2x2; inner cells trivially satisfied."""
    s = SlitherlinkState.empty(2, 2)
    _set_h(s, (0, 0), (0, 1), (2, 0), (2, 1))
    _set_v(s, (0, 0), (1, 0), (0, 2), (1, 2))
    ok, reason = is_solved(s)
    assert ok, reason


def test_solved_2x2_with_constrained_corners():
    """
    2x2 with cell (0,0)=2 (top-left has top + left edges = 2 lines).
    Outer perimeter loop satisfies cell (0,0)=2 since exactly 2 of its sides
    (top H[0][0] and left V[0][0]) are on the loop.
    """
    s = SlitherlinkState.empty(2, 2, cells={(0, 0): 2})
    _set_h(s, (0, 0), (0, 1), (2, 0), (2, 1))
    _set_v(s, (0, 0), (1, 0), (0, 2), (1, 2))
    ok, reason = is_solved(s)
    assert ok, reason


def test_solved_real_puzzle_001():
    """The genuine puzzle_001 solution we captured from a real run."""
    grid = """+---+   +---+---+---+
| 3 | . | .   2   . |
+   +---+   +---+   +
| .   2   1 | 3 | 3 |
+---+---+   +   +---+
  .   . | 2 | .   2
+---+---+   +---+---+
| .   .   0   .   2 |
+   +---+   +---+   +
| . | 3 | . | 3 | . |
+---+   +---+   +---+
"""
    s = load_from_text(grid)
    ok, reason = is_solved(s)
    assert ok, reason


# ---------- NEGATIVE CASES: NO LOOP ----------

def test_unsolved_empty_grid():
    s = SlitherlinkState.empty(3, 3)
    ok, reason = is_solved(s)
    assert not ok
    assert "no loop" in reason


def test_unsolved_cell_with_zero_unsatisfied_when_lines_exist():
    """Cell=0 + a line on its side → cell over-saturated → not solved."""
    s = SlitherlinkState.empty(1, 1, cells={(0, 0): 0})
    _set_h(s, (0, 0), (1, 0))
    _set_v(s, (0, 0), (0, 1))
    ok, reason = is_solved(s)
    assert not ok
    assert "0" in reason and "lines" in reason


# ---------- NEGATIVE CASES: CELL CONSTRAINT ----------

def test_unsolved_cell_under_satisfied():
    """Cell=3 but only 2 lines around it."""
    s = SlitherlinkState.empty(1, 1, cells={(0, 0): 3})
    _set_h(s, (0, 0), (1, 0))
    _set_v(s, (0, 0), (0, 1))
    # cell has 4 lines but constraint says 3 — over-satisfied is wrong direction;
    # remove the right edge to make it under (only 3 lines, but 1 dot has degree 1).
    s.v_edges[(0, 1)] = EdgeState.UNKNOWN
    ok, reason = is_solved(s)
    assert not ok
    # Should mention either dot degree (top-right corner) or cell count.
    assert ("dot" in reason) or ("cell" in reason), reason


def test_unsolved_cell_over_satisfied():
    """Cell=2 but 4 lines around it."""
    s = SlitherlinkState.empty(1, 1, cells={(0, 0): 2})
    _set_h(s, (0, 0), (1, 0))
    _set_v(s, (0, 0), (0, 1))
    ok, reason = is_solved(s)
    assert not ok
    assert ("cell" in reason) and ("2" in reason)


# ---------- NEGATIVE CASES: DOT DEGREE ----------

def test_unsolved_dot_degree_1_open_endpoint():
    """A single line with two endpoints — not a closed loop."""
    s = SlitherlinkState.empty(2, 2)
    _set_h(s, (0, 0))  # one line, two endpoints at (0,0) and (0,1)
    ok, reason = is_solved(s)
    assert not ok
    assert "dot" in reason


def test_unsolved_dot_degree_3_branch():
    """Branch at a dot — three line edges meet at the centre dot.

    Note: surrounding the centre with degree 3 is impossible to do without
    leaving other dots at degree 1 too (each LINE adds 1 to two dots), so
    is_solved may surface the degree-1 dots first. We only require that *some*
    dot-degree violation is reported.
    """
    s = SlitherlinkState.empty(2, 2)
    _set_h(s, (1, 0), (1, 1))
    _set_v(s, (0, 1))
    ok, reason = is_solved(s)
    assert not ok
    assert "dot" in reason


def test_unsolved_dot_degree_4_cross():
    """Cross at the centre dot of a 2x2 — four line edges meet there.
    Other dots at the line-tips will be degree 1; either is a valid failure mode.
    """
    s = SlitherlinkState.empty(2, 2)
    _set_h(s, (1, 0), (1, 1))
    _set_v(s, (0, 1), (1, 1))
    ok, reason = is_solved(s)
    assert not ok
    assert "dot" in reason


def test_unsolved_dot_degree_3_with_perimeter():
    """Construct a scenario where the *only* failing dot is one with degree 3."""
    # 2x2 outer perimeter (all degrees 2) plus one extra LINE that creates a
    # degree-3 dot but leaves only one new degree-1 dot.
    # Outer perimeter: H[0][0,1], H[2][0,1], V[0,1][0], V[0,1][2]. That gives
    # all 9 dots degree 0 or 2. Now add V[0][1] (centre vertical, top half) —
    # this raises dot (0,1) from degree 2 to 3 and dot (1,1) from 0 to 1.
    s = SlitherlinkState.empty(2, 2)
    _set_h(s, (0, 0), (0, 1), (2, 0), (2, 1))
    _set_v(s, (0, 0), (1, 0), (0, 2), (1, 2), (0, 1))
    ok, reason = is_solved(s)
    assert not ok
    # Either the 3-degree dot or the 1-degree dot triggers the failure.
    assert "dot" in reason


# ---------- NEGATIVE CASES: TOPOLOGY ----------

def test_unsolved_two_separate_loops():
    """Two disjoint unit loops in a 3x3 grid — solved must be one component."""
    s = SlitherlinkState.empty(3, 3)
    # Loop A: cell (0,0)
    _set_h(s, (0, 0), (1, 0))
    _set_v(s, (0, 0), (0, 1))
    # Loop B: cell (2,2)
    _set_h(s, (2, 2), (3, 2))
    _set_v(s, (2, 2), (2, 3))
    ok, reason = is_solved(s)
    assert not ok
    assert "components" in reason or "loop" in reason


def test_unsolved_open_path_no_closure():
    """A line of length 2 — degrees 1, 2, 1 — not closed."""
    s = SlitherlinkState.empty(1, 2)
    _set_h(s, (0, 0), (0, 1))  # two horizontal edges in a row
    ok, reason = is_solved(s)
    assert not ok
    assert "dot" in reason


# ---------- EDGE CASES ----------

def test_solved_unconstrained_cells_inside_loop():
    """3x3 outer perimeter loop with only some cells numbered."""
    cells = {(0, 0): 2, (1, 1): 0, (2, 2): 2}
    s = SlitherlinkState.empty(3, 3, cells=cells)
    _set_h(s, (0, 0), (0, 1), (0, 2), (3, 0), (3, 1), (3, 2))
    _set_v(s, (0, 0), (1, 0), (2, 0), (0, 3), (1, 3), (2, 3))
    ok, reason = is_solved(s)
    assert ok, reason


def test_unsolved_inner_cell_zero_violated_by_perimeter():
    """A 2x2 outer-perimeter loop with cell (0,0)=0 — but (0,0) has 2 perimeter sides."""
    s = SlitherlinkState.empty(2, 2, cells={(0, 0): 0})
    _set_h(s, (0, 0), (0, 1), (2, 0), (2, 1))
    _set_v(s, (0, 0), (1, 0), (0, 2), (1, 2))
    ok, reason = is_solved(s)
    assert not ok
    assert "0" in reason


def test_unsolved_zero_cell_with_blocked_edges_but_no_loop():
    """Cell=0 satisfied but no loop drawn anywhere → not solved."""
    s = SlitherlinkState.empty(1, 1, cells={(0, 0): 0})
    # All edges remain UNKNOWN; cell satisfied (0 lines), but no loop.
    ok, reason = is_solved(s)
    assert not ok
    assert "no loop" in reason


# ---------- ROUND-TRIP THROUGH PARSER ----------

def test_solved_round_trip_via_render():
    """A solved state, rendered to text and reparsed, should still be solved."""
    from core import render
    s = SlitherlinkState.empty(2, 2)
    _set_h(s, (0, 0), (0, 1), (2, 0), (2, 1))
    _set_v(s, (0, 0), (1, 0), (0, 2), (1, 2))
    text = render(s, show_blocked=False)
    s2 = load_from_text(text)
    ok, reason = is_solved(s2)
    assert ok, reason


# ---------- NUMBERED CELL EXACTNESS ----------

def test_unsolved_two_cell_grid_partial_satisfaction():
    """1x2 grid with cells (0,0)=2, (0,1)=2 and only outer perimeter — both
    cells have 3 sides on the loop (top, bottom, outer side) so they fail.
    """
    s = SlitherlinkState.empty(1, 2, cells={(0, 0): 2, (0, 1): 2})
    _set_h(s, (0, 0), (0, 1), (1, 0), (1, 1))
    _set_v(s, (0, 0), (0, 2))
    # Cell (0,0): top H[0][0] + bottom H[1][0] + left V[0][0] = 3 lines, but constraint 2.
    ok, reason = is_solved(s)
    assert not ok
    assert "cell" in reason and "2" in reason


def test_solved_1x2_with_3_constraint():
    """1x2 grid; cell (0,0)=3, cell (0,1)=3. Outer perimeter satisfies both
    (each cell has 3 outer sides on the loop)."""
    s = SlitherlinkState.empty(1, 2, cells={(0, 0): 3, (0, 1): 3})
    _set_h(s, (0, 0), (0, 1), (1, 0), (1, 1))
    _set_v(s, (0, 0), (0, 2))
    ok, reason = is_solved(s)
    assert ok, reason


if __name__ == "__main__":
    import sys
    failures = 0
    tests = [
        # positive
        test_solved_1x1_unit_loop_no_constraints,
        test_solved_1x1_with_cell_4_not_used,
        test_solved_2x2_outer_perimeter_no_numbers,
        test_solved_2x2_with_constrained_corners,
        test_solved_real_puzzle_001,
        test_solved_unconstrained_cells_inside_loop,
        test_solved_round_trip_via_render,
        test_solved_1x2_with_3_constraint,
        # negative
        test_unsolved_empty_grid,
        test_unsolved_cell_with_zero_unsatisfied_when_lines_exist,
        test_unsolved_cell_under_satisfied,
        test_unsolved_cell_over_satisfied,
        test_unsolved_dot_degree_1_open_endpoint,
        test_unsolved_dot_degree_3_branch,
        test_unsolved_dot_degree_4_cross,
        test_unsolved_dot_degree_3_with_perimeter,
        test_unsolved_two_separate_loops,
        test_unsolved_open_path_no_closure,
        test_unsolved_inner_cell_zero_violated_by_perimeter,
        test_unsolved_zero_cell_with_blocked_edges_but_no_loop,
        test_unsolved_two_cell_grid_partial_satisfaction,
    ]
    for t in tests:
        try:
            t()
            print(f"  ok  {t.__name__}")
        except AssertionError as e:
            failures += 1
            print(f"  FAIL {t.__name__}: {e}")
        except Exception as e:
            failures += 1
            print(f"  ERROR {t.__name__}: {type(e).__name__}: {e}")
    print(f"\n{len(tests) - failures}/{len(tests)} passed")
    sys.exit(1 if failures else 0)
