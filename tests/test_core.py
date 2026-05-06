"""Smoke tests for core/. Run with: python -m tests.test_core"""
from pathlib import Path

from core import (
    EdgeState,
    apply_edge,
    check_consistency,
    forced_moves,
    is_solved,
    load_from_text,
    render,
)

REPO = Path(__file__).resolve().parent.parent
PUZZLE_PATH = REPO / "legacy" / "slitherlink-batch-experiment" / "grid_step_0.txt"


def test_parse_and_render():
    state = load_from_text(PUZZLE_PATH.read_text())
    assert state.num_rows == 5, state.num_rows
    assert state.num_cols == 5, state.num_cols
    assert state.cells[(0, 0)] == 3
    assert state.cells[(3, 2)] == 0
    assert (0, 1) not in state.cells  # '.' = no number
    print("parse_and_render OK\n" + render(state))


def test_zero_cell_blocks_all_sides():
    state = load_from_text(PUZZLE_PATH.read_text())
    result = forced_moves(state)
    assert result.contradiction is None, result.contradiction
    # Cell (3,2)=0: all 4 surrounding edges must become BLOCKED.
    expected_edges = [
        ("H", 3, 2),
        ("H", 4, 2),
        ("V", 3, 2),
        ("V", 3, 3),
    ]
    for et, r, c in expected_edges:
        assert any(
            ch.edge_type == et and ch.row == r and ch.col == c
            and ch.new_state == EdgeState.BLOCKED
            for ch in result.changes
        ), f"missing forced block on {et}[{r}][{c}]"
    print(f"zero_cell_blocks_all_sides OK ({len(result.changes)} forced moves)")


def test_apply_edge_propagates():
    state = load_from_text(PUZZLE_PATH.read_text())
    # Apply edge top of cell (0,0)=3 — should propagate around that cell.
    result = apply_edge(state, "H", 0, 0, "line")
    assert result.contradiction is None, result.contradiction
    print(f"apply_edge_propagates: {len(result.changes)} total changes")
    print(render(state))


def test_consistency_clean_on_empty():
    state = load_from_text(PUZZLE_PATH.read_text())
    issues = check_consistency(state)
    assert issues == [], issues
    solved, reason = is_solved(state)
    assert not solved, "empty grid is not solved"
    print("consistency_clean_on_empty OK")


def test_contradiction_when_overfilling_zero():
    state = load_from_text(PUZZLE_PATH.read_text())
    # Try to put a line on a side of (3,2)=0.
    result = apply_edge(state, "H", 3, 2, "line")
    assert result.contradiction is not None, "expected contradiction on 0-cell"
    print(f"contradiction_when_overfilling_zero OK: {result.contradiction}")


if __name__ == "__main__":
    test_parse_and_render()
    test_zero_cell_blocks_all_sides()
    test_apply_edge_propagates()
    test_consistency_clean_on_empty()
    test_contradiction_when_overfilling_zero()
    print("\nAll smoke tests passed.")
